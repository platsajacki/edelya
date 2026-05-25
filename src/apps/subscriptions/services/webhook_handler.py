from dataclasses import dataclass
from enum import StrEnum

from django.db import transaction
from django.utils import timezone

from yookassa.payment import PaymentResponse
from yookassa.payment_method import PaymentMethodResponse

from apps.marketing.models.model_enums import MessageTemplateName
from apps.marketing.services.sender import NotificationSender, fmt_date
from apps.subscriptions.models import Subscription, Tariff
from apps.subscriptions.models.model_enums import PaymentStatus, SubscriptionStatus
from apps.subscriptions.models.payment_methods import PaymentMethod
from apps.subscriptions.models.payments import Payment
from apps.subscriptions.services.sync_controler import payment_sync_flag_controler
from apps.subscriptions.services.tax_check import TaxCheckSender
from apps.users.models.consents import ConsentLog
from apps.users.models.model_enums import ConsentAction, ConsentType
from core.base.services import BaseService
from core.logging_handlers import loki_logger, tg_logger


class WebhookAction(StrEnum):
    TRIAL_CARD_BINDING = 'trial_card_binding'
    CARD_BINDING = 'card_binding'
    FIRST_PAYMENT = 'first_payment'
    RECURRING = 'recurring'
    UPGRADE = 'upgrade'


class WebhookEventType(StrEnum):
    PAYMENT_SUCCEEDED = 'payment.succeeded'
    PAYMENT_CANCELED = 'payment.canceled'
    PAYMENT_METHOD_ACTIVE = 'payment_method.active'


@dataclass
class PaymentSucceededHandler(BaseService):
    payment: Payment
    yoo_payment: PaymentResponse

    def _log_payment_method_storage_consent(self) -> None:
        try:
            ConsentLog.objects.create(
                user=self.payment.user,
                consent_type=ConsentType.PAYMENT_METHOD_STORAGE,
                action=ConsentAction.GRANTED,
            )
        except Exception:
            loki_logger.error(
                self.get_log_msg(f'Failed to log payment method storage consent for user {self.payment.user_id}'),
                exc_info=True,
            )

    def _upsert_payment_method(self) -> PaymentMethod:
        yookassa_payment_method = self.yoo_payment.payment_method
        card = getattr(yookassa_payment_method, 'card', None)
        payment_method, created = PaymentMethod.objects.update_or_create(
            user=self.payment.user,
            defaults={
                'yookassa_payment_method_id': yookassa_payment_method.id,
                'payment_method_type': yookassa_payment_method.type,
                'card_last4': getattr(card, 'last4', None),
                'card_type': getattr(card, 'card_type', None),
                'title': yookassa_payment_method.title,
                'is_active': True,
            },
        )
        if created:
            self._log_payment_method_storage_consent()
        return payment_method

    def _activate_subscription(self, subscription: Subscription, tariff: Tariff, payment_method: PaymentMethod) -> None:
        now = timezone.now()
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.tariff = tariff
        subscription.current_period_start = now
        subscription.current_period_end = tariff.get_next_period_end(now)
        subscription.auto_renew = True
        subscription.payment_method = payment_method
        subscription.pending_tariff = None
        subscription.cancelled_at = None
        subscription.save(
            update_fields=[
                'status',
                'tariff',
                'current_period_start',
                'current_period_end',
                'auto_renew',
                'payment_method',
                'pending_tariff',
                'cancelled_at',
            ]
        )

    def _renew_subscription(self, subscription: Subscription, payment_method: PaymentMethod) -> None:
        tariff = subscription.pending_tariff or subscription.tariff
        if not tariff:
            loki_logger.error(self.get_log_msg(f'Subscription {subscription.id} has no tariff during renewal'))
            return
        period_start = subscription.current_period_end or timezone.now()
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.tariff = tariff
        subscription.pending_tariff = None
        subscription.current_period_start = period_start
        subscription.current_period_end = tariff.get_next_period_end(period_start)
        subscription.payment_method = payment_method
        subscription.save(
            update_fields=[
                'status',
                'tariff',
                'pending_tariff',
                'current_period_start',
                'current_period_end',
                'payment_method',
            ]
        )

    def send_notification(self, tamplate_name: MessageTemplateName, variables: dict) -> None:
        NotificationSender(
            self.payment.user,
            tamplate_name,
            variables,
        )()

    @transaction.atomic
    def act(self) -> None:
        if self.payment.status == PaymentStatus.SUCCEEDED:
            return
        payment_method = self._upsert_payment_method()
        self.payment.status = PaymentStatus.SUCCEEDED
        self.payment.paid_at = timezone.now()
        self.payment.payment_method = payment_method
        self.payment.save(update_fields=['status', 'paid_at', 'payment_method'])
        action = self.payment.metadata.get('action')
        if action == WebhookAction.FIRST_PAYMENT:
            tariff = Tariff.objects.get(id=self.payment.metadata['tariff_id'])
            self._activate_subscription(self.payment.subscription, tariff, payment_method)
            self.send_notification(
                MessageTemplateName.SUBSCRIPTION_FIRST_PAYMENT_SUCCEEDED,
                {
                    'tariff_name': tariff.name,
                    'amount': str(self.payment.amount),
                    'currency': str(self.payment.currency),
                    'period_end': fmt_date(self.payment.subscription.current_period_end),
                },
            )
            TaxCheckSender(self.payment, f'Первый платеж по подписке на сервис Edelya — {tariff.name}')()
        elif action == WebhookAction.RECURRING:
            self._renew_subscription(self.payment.subscription, payment_method)
            self.send_notification(
                MessageTemplateName.SUBSCRIPTION_RECURRING_PAYMENT_SUCCEEDED,
                {
                    'tariff_name': self.payment.subscription.tariff.name,
                    'amount': str(self.payment.amount),
                    'currency': str(self.payment.currency),
                    'period_end': fmt_date(self.payment.subscription.current_period_end),
                },
            )
            service_name = f'Рекуррентный платеж по подписке на сервис Edelya — {self.payment.subscription.tariff.name}'
            TaxCheckSender(self.payment, service_name)()
        else:
            tg_logger.warning(
                'PaymentSucceededHandler: unexpected action %r for payment %s, skipping subscription update',
                action,
                self.payment.id,
            )


@dataclass
class PaymentCanceledHandler(BaseService):
    payment: Payment
    yoo_payment: PaymentResponse

    @transaction.atomic
    def act(self) -> None:
        if self.payment.status == PaymentStatus.CANCELED:
            return
        cancellation_details = getattr(self.yoo_payment, 'cancellation_details', None)
        reason = getattr(cancellation_details, 'reason', '') or ''
        self.payment.status = PaymentStatus.CANCELED
        self.payment.cancellation_reason = reason
        self.payment.save(update_fields=['status', 'cancellation_reason'])
        subscription = self.payment.subscription
        NotificationSender(
            self.payment.user,
            MessageTemplateName.SUBSCRIPTION_PAYMENT_FAILED,
            {
                'tariff_name': subscription.tariff.name if subscription and subscription.tariff else '—',
                'amount': str(self.payment.amount),
                'currency': str(self.payment.currency),
            },
        )()


@dataclass
class PaymentMethodActiveHandler(BaseService):
    payment: Payment
    yookassa_payment_method: PaymentMethodResponse

    def _upsert_payment_method(self) -> PaymentMethod:
        card = getattr(self.yookassa_payment_method, 'card', None)
        payment_method, _ = PaymentMethod.objects.update_or_create(
            user=self.payment.user,
            defaults={
                'yookassa_payment_method_id': self.yookassa_payment_method.id,
                'payment_method_type': self.yookassa_payment_method.type,
                'card_last4': getattr(card, 'last4', None),
                'card_type': getattr(card, 'card_type', None),
                'title': self.yookassa_payment_method.title,
                'is_active': True,
            },
        )
        return payment_method

    @transaction.atomic
    def act(self) -> None:
        if self.payment.status == PaymentStatus.SUCCEEDED:
            return
        payment_method = self._upsert_payment_method()
        subscription = self.payment.subscription
        subscription.payment_method = payment_method
        update_fields = ['payment_method']
        if self.payment.metadata.get('action') == WebhookAction.TRIAL_CARD_BINDING:
            tariff_id = self.payment.metadata.get('tariff_id')
            if tariff_id:
                subscription.pending_tariff = Tariff.objects.filter(id=tariff_id).first()
                update_fields.append('pending_tariff')
        subscription.save(update_fields=update_fields)
        self.payment.status = PaymentStatus.SUCCEEDED
        self.payment.payment_method = payment_method
        self.payment.paid_at = timezone.now()
        self.payment.save(update_fields=['status', 'payment_method', 'paid_at'])
        NotificationSender(
            self.payment.user,
            MessageTemplateName.SUBSCRIPTION_CARD_BOUND,
            {'card_name': payment_method.card_name},
        )()


@dataclass
class WebhookHandler(BaseService):
    event: str
    object_data: dict

    def _get_payment(self, yookassa_id: str) -> Payment:
        try:
            return (
                Payment.objects.select_related('user', 'subscription', 'subscription__tariff')
                .select_for_update()
                .get(yookassa_payment_id=yookassa_id)
            )
        except Payment.DoesNotExist:
            loki_logger.warning('Payment not found for YooKassa ID: %s', self.object_data)
            raise

    def _check_idempotence(self) -> bool:
        idempotence_key = self.object_data.get('metadata', {}).get('idempotence_key')
        if idempotence_key:
            if payment_sync_flag_controler.check_payment_sync_flag(idempotence_key):
                loki_logger.info(
                    'Payment with idempotence_key=%s was processed synchronously, skipping webhook',
                    idempotence_key,
                )
                return True
        else:
            loki_logger.warning(
                'No idempotence_key in webhook metadata for event %s and object %s',
                self.event,
                self.object_data,
            )
        return False

    def act(self) -> None:
        try:
            event_type = WebhookEventType(self.event)
        except ValueError:
            loki_logger.info('Unsupported YooKassa webhook event: %s', self.event)
            return
        loki_logger.info('Processing YooKassa webhook event: %s', event_type)
        if (
            event_type in (WebhookEventType.PAYMENT_SUCCEEDED, WebhookEventType.PAYMENT_CANCELED, WebhookAction.UPGRADE)
            and self._check_idempotence()
        ):
            return
        if event_type == WebhookEventType.PAYMENT_SUCCEEDED:
            yoo_payment = PaymentResponse(self.object_data)
            PaymentSucceededHandler(
                payment=self._get_payment(yoo_payment.id),
                yoo_payment=yoo_payment,
            )()
        elif event_type == WebhookEventType.PAYMENT_CANCELED:
            yoo_payment = PaymentResponse(self.object_data)
            PaymentCanceledHandler(
                payment=self._get_payment(yoo_payment.id),
                yoo_payment=yoo_payment,
            )()
        elif event_type == WebhookEventType.PAYMENT_METHOD_ACTIVE:
            yookassa_payment_method = PaymentMethodResponse(self.object_data)
            PaymentMethodActiveHandler(
                payment=self._get_payment(yookassa_payment_method.id),
                yookassa_payment_method=yookassa_payment_method,
            )()
