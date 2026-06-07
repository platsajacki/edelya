from datetime import datetime

from apps.subscriptions.exceptions import PaymentPendingRecurringError
from apps.subscriptions.models import Subscription, Tariff
from apps.subscriptions.models.model_enums import PaymentStatus, SubscriptionStatus
from apps.subscriptions.services.webhook_handler import WebhookAction
from apps.subscriptions.tasks.base import RecurringTaskService
from core import celery_app
from core.logging_handlers import loki_logger


class ChargePastDueService(RecurringTaskService):
    def _apply_tariff(self, subscription: Subscription, tariff: Tariff, period_start: datetime) -> None:
        _ = period_start
        subscription.tariff = tariff
        subscription.pending_tariff = None

    def process_subscription(self, subscription: Subscription, tariff: Tariff) -> None:
        self.check_pending_recurring_payment(subscription)
        payment = self.create_payment(subscription, tariff, action=WebhookAction.RECURRING)
        loki_logger.info(
            self.get_log_msg(f'Created past-due retry payment {payment.id!r} for subscription {subscription.id!r}.')
        )
        period_start = self.ensure_current_period_end(subscription)
        try:
            yoo_payment_response = self.try_charge_payment(
                payment, tariff, subscription, description=f'Повторное списание подписки "{tariff.name}"'
            )
        except PaymentPendingRecurringError as e:
            loki_logger.warning(self.get_log_msg(f'Skipping past-due retry. {e.message}'))
            self.process_payment(
                payment,
                tariff,
                subscription,
                succeeded=False,
                cancellation_reason=str(e),
                period_start=period_start,
                failed_status=SubscriptionStatus.EXPIRED,
            )
            return
        status = PaymentStatus(yoo_payment_response.status)
        if status == PaymentStatus.SUCCEEDED:
            self.process_payment(
                payment,
                tariff,
                subscription,
                succeeded=True,
                period_start=period_start,
                failed_status=SubscriptionStatus.EXPIRED,
            )
        else:
            cancellation_details = getattr(yoo_payment_response, 'cancellation_details', None)
            reason = getattr(cancellation_details, 'reason', '') or 'Unknown reason'
            self.process_payment(
                payment,
                tariff,
                subscription,
                succeeded=False,
                cancellation_reason=reason,
                period_start=period_start,
                failed_status=SubscriptionStatus.EXPIRED,
            )

    def act(self) -> int:
        subscriptions = Subscription.objects.get_past_due_for_retry()
        count = 0
        for subscription in subscriptions:
            try:
                tariff = subscription.pending_tariff or subscription.tariff
                self.process_subscription(subscription, tariff=tariff)
                count += 1
            except PaymentPendingRecurringError as e:
                loki_logger.warning(self.get_log_msg(f'Skipping past-due retry. {e.message}'), exc_info=True)
                continue
            except Exception as e:
                loki_logger.error(
                    self.get_log_msg(f'Error processing subscription {subscription.id!r}: {e}'), exc_info=True
                )
                continue
        return count


@celery_app.task
def process_past_due_charge() -> str:
    """
    Вторая и последняя попытка списания для PAST_DUE-подписок.
    Запускается раз в CHECK_SUBSCRIPTION_PAYMENT_TIMEDELTA. При неуспехе → EXPIRED.
    Обрабатывает подписки, у которых grace period истекает в следующие CHECK_SUBSCRIPTION_PAYMENT_TIMEDELTA.

    current_period_start + GRACE_PERIOD_DAYS <= now + CHECK_SUBSCRIPTION_PAYMENT_TIMEDELTA
    ↔ current_period_start <= now + CHECK_SUBSCRIPTION_PAYMENT_TIMEDELTA - GRACE_PERIOD_DAYS
    """
    service = ChargePastDueService()
    charged = service()
    return service.get_log_msg(f'Charged {charged} past-due subscriptions.')
