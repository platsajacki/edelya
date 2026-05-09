from datetime import datetime

from django.utils import timezone

from apps.subscriptions.exceptions import PaymentPendingRecurringError, SubscriptionDoesHavePendingTariffError
from apps.subscriptions.models import Subscription, Tariff
from apps.subscriptions.models.model_enums import PaymentStatus, SubscriptionStatus
from apps.subscriptions.services.webhook_handler import WebhookAction
from apps.subscriptions.tasks.base import RecurringTaskService
from core import celery_app
from core.logging_handlers import loki_logger


class ChargeTrialToPaidService(RecurringTaskService):
    def _ensure_trial_ended(self, subscription: Subscription) -> datetime:
        if subscription.trial_ended_at is None:
            subscription.trial_ended_at = timezone.now()
        return subscription.trial_ended_at

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
        self.check_pending_recurring_payment(subscription)
        payment = self.create_payment(subscription, pending_tariff, action=WebhookAction.FIRST_PAYMENT)
        loki_logger.info(
            self.get_log_msg(
                f'Created payment {payment.id!r} for subscription {subscription.id!r} to charge trial to paid.'
            )
        )
        trial_ended_at = self._ensure_trial_ended(subscription)
        try:
            yoo_payment_response = self.try_charge_payment(
                payment,
                pending_tariff,
                subscription,
                description=f'Активация подписки "{pending_tariff.name}" после пробного периода',
            )
        except PaymentPendingRecurringError as e:
            loki_logger.warning(self.get_log_msg(f'Skipping trial to paid conversion. {e.message}'))
            self.process_payment(
                payment,
                pending_tariff,
                subscription,
                succeeded=False,
                period_start=trial_ended_at,
                failed_status=SubscriptionStatus.PAST_DUE,
                cancellation_reason=str(e),
            )
            return
        status = PaymentStatus(yoo_payment_response.status)
        if status == PaymentStatus.SUCCEEDED:
            self.process_payment(
                payment,
                pending_tariff,
                subscription,
                succeeded=True,
                period_start=trial_ended_at,
                failed_status=SubscriptionStatus.PAST_DUE,
            )
        else:
            cancellation_details = getattr(yoo_payment_response, 'cancellation_details', None)
            reason = getattr(cancellation_details, 'reason', '') or 'Unknown reason'
            self.process_payment(
                payment,
                pending_tariff,
                subscription,
                succeeded=False,
                period_start=trial_ended_at,
                failed_status=SubscriptionStatus.PAST_DUE,
                cancellation_reason=reason,
            )

    def act(self) -> int:
        subscriptions = Subscription.objects.get_trial_to_paid()
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
    Запускается раз в CHECK_SUBSCRIPTION_PAYMENT_TIMEDELTA и обрабатывает все подписки,
    у которых trial_ended_at <= now + CHECK_SUBSCRIPTION_PAYMENT_TIMEDELTA.
    """
    charged = ChargeTrialToPaidService()()
    return f'Charged {charged} trials to paid.'
