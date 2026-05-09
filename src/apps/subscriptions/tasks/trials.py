from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from yookassa.payment import PaymentResponse

from apps.subscriptions.exceptions import PaymentPendingRecurringError, SubscriptionDoesHavePendingTariffError
from apps.subscriptions.models import Payment, Subscription, Tariff
from apps.subscriptions.models.model_enums import PaymentStatus, PaymentType, SubscriptionStatus
from apps.subscriptions.services.webhook_handler import WebhookAction
from apps.subscriptions.services.yookassa_payments import yookassa_service
from apps.subscriptions.tasks.base import RecurringTaskService
from core import celery_app
from core.logging_handlers import loki_logger


@dataclass
class ChargeTrialToPaidService(RecurringTaskService):
    trial_ended_at__lte: datetime

    def create_payment(self, subscription: Subscription, pending_tariff: Tariff) -> Payment:
        return Payment.objects.create(
            subscription=subscription,
            user=subscription.user,
            amount=pending_tariff.price,
            payment_type=PaymentType.RECURRING,
            status=PaymentStatus.PENDING,
            idempotence_key=str(uuid4()),
            metadata={
                'action': WebhookAction.FIRST_PAYMENT,
                'tariff_id': str(pending_tariff.id),
            },
        )

    def try_charge_payment(
        self, payment: Payment, pending_tariff: Tariff, subscription: Subscription
    ) -> PaymentResponse:
        try:
            yoo_payment_method_id = getattr(subscription.payment_method, 'yookassa_payment_method_id', None)
            return yookassa_service.create_payment(
                amount=pending_tariff.price,
                payment_method_id=yoo_payment_method_id,
                capture=True,
                idempotence_key=str(payment.idempotence_key),
                description=f'Активация подписки "{pending_tariff.name}" после пробного периода',
                metadata=payment.metadata,
            )
        except Exception as e:
            raise PaymentPendingRecurringError(subscription_id=payment.subscription_id, message=str(e)) from e

    @transaction.atomic
    def process_payment(
        self,
        payment: Payment,
        pending_tariff: Tariff,
        subscription: Subscription,
        succeeded: bool,
        cancellation_reason: str | None = None,
    ) -> None:
        trial_ended_at = self._ensure_trial_ended(subscription)
        self._apply_tariff(
            subscription=subscription,
            tariff=pending_tariff,
            period_start=trial_ended_at,
        )
        if succeeded:
            self._process_successful_payment(payment, subscription)
        else:
            self._process_failed_payment(
                payment=payment,
                subscription=subscription,
                cancellation_reason=cancellation_reason,
            )
        self._save_subscription_after_payment(subscription)

    def _ensure_trial_ended(self, subscription: Subscription) -> datetime:
        if subscription.trial_ended_at is None:
            subscription.trial_ended_at = timezone.now()

        return subscription.trial_ended_at

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
    ) -> None:
        payment.status = PaymentStatus.SUCCEEDED
        payment.paid_at = timezone.now()
        payment.save(update_fields=['status', 'paid_at'])
        subscription.status = SubscriptionStatus.ACTIVE
        loki_logger.info(
            self.get_log_msg(
                f'Processed successful payment {payment.id!r} for subscription {subscription.id!r}. '
                f'Status set to ACTIVE.'
            )
        )

    def _process_failed_payment(
        self,
        payment: Payment,
        subscription: Subscription,
        cancellation_reason: str | None = None,
    ) -> None:
        payment.status = PaymentStatus.CANCELED
        payment.cancellation_reason = cancellation_reason or 'Unknown reason'
        payment.save(update_fields=['status', 'cancellation_reason'])
        subscription.status = SubscriptionStatus.PAST_DUE
        loki_logger.info(
            self.get_log_msg(
                f'Cancelled payment {payment.id!r} '
                f'for subscription {subscription.id!r} due to failed payment. Reason: {cancellation_reason}'
            )
        )

    def _save_subscription_after_payment(self, subscription: Subscription) -> None:
        subscription.save(
            update_fields=[
                'status',
                'tariff',
                'pending_tariff',
                'current_period_start',
                'current_period_end',
                'trial_ended_at',
            ],
        )

    def process_subscription(self, subscription: Subscription, pending_tariff: Tariff) -> None:
        self.check_pending_recurring_payment(subscription, created_at__gte=self.trial_ended_at__lte)
        payment = self.create_payment(subscription, pending_tariff)
        loki_logger.info(
            self.get_log_msg(
                f'Created payment {payment.id!r} for subscription {subscription.id!r} to charge trial to paid.'
            )
        )
        try:
            yoo_payment_response = self.try_charge_payment(payment, pending_tariff, subscription)
        except PaymentPendingRecurringError as e:
            loki_logger.warning(self.get_log_msg(f'Skipping trial to paid conversion. {e.message}'))
            self.process_payment(payment, pending_tariff, subscription, succeeded=False, cancellation_reason=str(e))
            return
        status = PaymentStatus(yoo_payment_response.status)
        if status == PaymentStatus.SUCCEEDED:
            self.process_payment(payment, pending_tariff, subscription, succeeded=True)
        else:
            cancellation_details = getattr(yoo_payment_response, 'cancellation_details', None)
            reason = getattr(cancellation_details, 'reason', '') or 'Unknown reason'
            self.process_payment(payment, pending_tariff, subscription, succeeded=False, cancellation_reason=reason)

    def act(self) -> int:
        subscriptions = Subscription.objects.get_trial_to_paid(trial_ended_at__lte=self.trial_ended_at__lte)
        count = 0
        for subscription in subscriptions:
            try:
                if subscription.pending_tariff is None:
                    raise SubscriptionDoesHavePendingTariffError(subscription.id)
                self.process_subscription(subscription, pending_tariff=subscription.pending_tariff)
                count += 1
            except (SubscriptionDoesHavePendingTariffError, PaymentPendingRecurringError) as e:
                loki_logger.warning(self.get_log_msg(f'Skipping trial to paid conversion. {e.message}'), exc_info=True)
                continue
            except Exception as e:
                loki_logger.error(
                    self.get_log_msg(f'Error processing subscription {subscription.id!r}: {e}'), exc_info=True
                )
                continue
        return count


@celery_app.task
def process_trial_to_paid() -> str:
    """
    Переводит подписки из статуса TRIAL в статус ACTIVE.
    Запускается раз в 5 минут и обрабатывает все подписки, у которых trial_ended_at <= now -5 минут.
    """
    now = timezone.now() + timedelta(minutes=5)
    charged = ChargeTrialToPaidService(now)()
    return f'Charged {charged} trials to paid.'
