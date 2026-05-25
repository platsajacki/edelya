from datetime import datetime
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from yookassa.payment import PaymentResponse

from apps.marketing.models.model_enums import MessageTemplateName
from apps.marketing.services.sender import NotificationSender, fmt_date
from apps.subscriptions.exceptions import PaymentPendingRecurringError
from apps.subscriptions.models import Payment, Subscription, Tariff
from apps.subscriptions.models.model_enums import PaymentStatus, PaymentType, SubscriptionStatus
from apps.subscriptions.services.sync_controler import payment_sync_flag_controler
from apps.subscriptions.services.tax_check import TaxCheckSender
from apps.subscriptions.services.webhook_handler import WebhookAction
from apps.subscriptions.services.yookassa_payments import yookassa_service
from core.base.services import TaskService
from core.logging_handlers import loki_logger


class RecurringTaskService(TaskService):
    def check_pending_recurring_payment(self, subscription: Subscription) -> None:
        has_pending = Payment.objects.has_pending_recurring_payment(subscription)
        if has_pending:
            raise PaymentPendingRecurringError(subscription.id)

    def ensure_current_period_end(self, subscription: Subscription) -> datetime:
        if subscription.current_period_end is None:
            raise PaymentPendingRecurringError(
                subscription.id, 'Cannot process renewal: current_period_end is not set.'
            )
        return subscription.current_period_end

    def _apply_tariff(
        self,
        subscription: Subscription,
        tariff: Tariff,
        period_start: datetime,
    ) -> None:
        subscription.tariff = tariff
        subscription.pending_tariff = None
        subscription.current_period_start = period_start
        subscription.current_period_end = tariff.get_next_period_end(period_start)

    def _process_successful_payment(
        self,
        payment: Payment,
        subscription: Subscription,
        service_name: str,
    ) -> None:
        payment.status = PaymentStatus.SUCCEEDED
        payment.paid_at = timezone.now()
        if subscription.payment_method and not payment.payment_method:
            payment.payment_method = subscription.payment_method
        payment.save(update_fields=['status', 'paid_at', 'payment_method'])
        subscription.status = SubscriptionStatus.ACTIVE
        loki_logger.info(
            self.get_log_msg(
                f'Processed successful payment {payment.id!r} for subscription {subscription.id!r}. '
                f'Status set to ACTIVE.'
            )
        )
        action = payment.metadata.get('action')
        if action == WebhookAction.FIRST_PAYMENT:
            NotificationSender(
                payment.user,
                MessageTemplateName.SUBSCRIPTION_FIRST_PAYMENT_SUCCEEDED,
                {
                    'tariff_name': subscription.tariff.name,
                    'amount': str(payment.amount),
                    'currency': str(payment.currency),
                    'period_end': fmt_date(subscription.current_period_end),
                },
            )()
        elif action == WebhookAction.RECURRING:
            NotificationSender(
                payment.user,
                MessageTemplateName.SUBSCRIPTION_RECURRING_PAYMENT_SUCCEEDED,
                {
                    'tariff_name': subscription.tariff.name,
                    'amount': str(payment.amount),
                    'currency': str(payment.currency),
                    'period_end': fmt_date(subscription.current_period_end),
                },
            )()
        TaxCheckSender(payment, service_name)()

    def _process_failed_payment(
        self,
        payment: Payment,
        subscription: Subscription,
        cancellation_reason: str | None = None,
        failed_status: SubscriptionStatus = SubscriptionStatus.PAST_DUE,
    ) -> None:
        payment.status = PaymentStatus.CANCELED
        payment.cancellation_reason = cancellation_reason or 'Unknown reason'
        payment.save(update_fields=['status', 'cancellation_reason'])
        subscription.status = failed_status
        loki_logger.info(
            self.get_log_msg(
                f'Cancelled payment {payment.id!r} '
                f'for subscription {subscription.id!r} due to failed payment. Reason: {cancellation_reason}'
            )
        )
        NotificationSender(
            payment.user,
            MessageTemplateName.SUBSCRIPTION_PAYMENT_FAILED,
            {
                'tariff_name': subscription.tariff.name,
                'amount': str(payment.amount),
                'currency': str(payment.currency),
            },
        )()

    def _save_subscription_after_payment(self, subscription: Subscription) -> None:
        subscription.save(
            update_fields=[
                'status',
                'tariff',
                'pending_tariff',
                'current_period_start',
                'current_period_end',
            ],
        )

    def create_payment(self, subscription: Subscription, tariff: Tariff, action: WebhookAction) -> Payment:
        idempotence_key = str(uuid4())
        return Payment.objects.create(
            subscription=subscription,
            user=subscription.user,
            amount=tariff.price,
            payment_type=PaymentType.RECURRING,
            status=PaymentStatus.PENDING,
            idempotence_key=idempotence_key,
            metadata={
                'action': action,
                'tariff_id': str(tariff.id),
                'idempotence_key': idempotence_key,
            },
        )

    def try_charge_payment(
        self, payment: Payment, tariff: Tariff, subscription: Subscription, description: str
    ) -> PaymentResponse:
        try:
            payment_sync_flag_controler.set_payment_sync_flag(str(payment.idempotence_key))
            yoo_payment_method_id = getattr(subscription.payment_method, 'yookassa_payment_method_id', None)
            yoo_response = yookassa_service.create_payment(
                amount=tariff.price,
                payment_method_id=yoo_payment_method_id,
                capture=True,
                idempotence_key=str(payment.idempotence_key),
                description=description,
                metadata=payment.metadata,
            )
            payment.yookassa_payment_id = yoo_response.id
            payment.save(update_fields=['yookassa_payment_id'])
            return yoo_response
        except Exception as e:
            raise PaymentPendingRecurringError(subscription_id=payment.subscription_id, message=str(e)) from e

    @transaction.atomic
    def process_payment(
        self,
        payment: Payment,
        tariff: Tariff,
        subscription: Subscription,
        succeeded: bool,
        period_start: datetime,
        failed_status: SubscriptionStatus,
        cancellation_reason: str | None = None,
    ) -> None:
        self._apply_tariff(subscription=subscription, tariff=tariff, period_start=period_start)
        if succeeded:
            self._process_successful_payment(
                payment, subscription, service_name=f'Подписка на сервис Edelya — {tariff.name}'
            )
        else:
            self._process_failed_payment(
                payment=payment,
                subscription=subscription,
                cancellation_reason=cancellation_reason,
                failed_status=failed_status,
            )
        self._save_subscription_after_payment(subscription)
