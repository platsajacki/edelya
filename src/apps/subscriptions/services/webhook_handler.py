from dataclasses import dataclass
from enum import StrEnum

from django.db import transaction
from django.utils import timezone

from yookassa.payment import PaymentResponse
from yookassa.payment_method import PaymentMethodResponse

from apps.subscriptions.models import Subscription, Tariff
from apps.subscriptions.models.model_enums import PaymentStatus, SubscriptionStatus
from apps.subscriptions.models.payment_methods import PaymentMethod
from apps.subscriptions.models.payments import Payment
from core.base.services import BaseService
from core.logging_handlers import loki_logger


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

    def _upsert_payment_method(self) -> PaymentMethod:
        yookassa_payment_method = self.yoo_payment.payment_method
        card = getattr(yookassa_payment_method, 'card', None)
        payment_method, _ = PaymentMethod.objects.update_or_create(
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
        if not subscription.tariff:
            loki_logger.error('Subscription %s has no tariff during renewal', subscription.id)
            return
        period_start = subscription.current_period_end or timezone.now()
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.current_period_start = period_start
        subscription.current_period_end = subscription.tariff.get_next_period_end(period_start)
        subscription.payment_method = payment_method
        subscription.save(update_fields=['status', 'current_period_start', 'current_period_end', 'payment_method'])

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
        elif action == WebhookAction.UPGRADE:
            pass  # subscription already updated synchronously during upgrade
        else:
            self._renew_subscription(self.payment.subscription, payment_method)


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


@dataclass
class WebhookHandler(BaseService):
    event: str
    object_data: dict

    def _get_payment(self, yookassa_id: str) -> Payment:
        return Payment.objects.select_related('user', 'subscription', 'subscription__tariff').get(
            yookassa_payment_id=yookassa_id
        )

    def act(self) -> None:
        try:
            event_type = WebhookEventType(self.event)
        except ValueError:
            loki_logger.info('Unsupported YooKassa webhook event: %s', self.event)
            return
        loki_logger.info('Processing YooKassa webhook event: %s', event_type)
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
