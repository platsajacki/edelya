from apps.marketing.models.model_enums import MessageTemplateName
from apps.marketing.services.sender import NotificationSender
from apps.subscriptions.models import Payment, Subscription
from apps.subscriptions.models.model_enums import SubscriptionStatus
from apps.subscriptions.tasks.base import RecurringTaskService
from core import celery_app
from core.logging_handlers import loki_logger


class ExpireTrialsService(RecurringTaskService):
    def act(self) -> int:
        count = Subscription.objects.get_abandoned_trials().update(status=SubscriptionStatus.EXPIRED)
        return count


class ExpirePastDueService(RecurringTaskService):
    def act(self) -> int:
        subscriptions = Subscription.objects.get_past_due_for_expiry()
        count = 0
        for subscription in subscriptions:
            if Payment.objects.has_pending_recurring_payment(subscription):
                loki_logger.warning(
                    self.get_log_msg(
                        f'Skipping expiry of subscription {subscription.id!r} due to pending recurring payment.'
                    )
                )
                continue
            subscription.status = SubscriptionStatus.EXPIRED
            subscription.save(update_fields=['status'])
            NotificationSender(
                subscription.user,
                MessageTemplateName.SUBSCRIPTION_EXPIRED,
                {'tariff_name': subscription.tariff.name},
            )()
            count += 1
        return count


class ExpireCancelledService(RecurringTaskService):
    def act(self) -> int:
        count = Subscription.objects.get_cancelled_for_expiry().update(status=SubscriptionStatus.EXPIRED)
        return count


@celery_app.task
def expire_trials_without_payment() -> str:
    """
    Переводит в EXPIRED брошенные Trial-подписки (pending_tariff = None) с истёкшим триалом.
    """
    service = ExpireTrialsService()
    count = service()
    return service.get_log_msg(f'Expired {count} abandoned trials.')


@celery_app.task
def expire_past_due_subscriptions() -> str:
    """
    Страховочный fallback: переводит в EXPIRED PAST_DUE-подписки после истечения grace period.
    """
    service = ExpirePastDueService()
    count = service()
    return service.get_log_msg(f'Expired {count} past-due subscriptions.')


@celery_app.task
def expire_cancelled_subscriptions() -> str:
    """
    Переводит в EXPIRED ACTIVE-подписки с auto_renew=False и истёкшим current_period_end.
    """
    service = ExpireCancelledService()
    count = service()
    return service.get_log_msg(f'Expired {count} cancelled subscriptions.')
