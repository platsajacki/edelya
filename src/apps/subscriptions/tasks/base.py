from datetime import datetime

from apps.subscriptions.exceptions import PaymentPendingRecurringError
from apps.subscriptions.models import Payment, Subscription
from core.base.services import TaskService


class RecurringTaskService(TaskService):
    def check_pending_recurring_payment(self, subscription: Subscription, created_at__gte: datetime) -> None:
        has_pending_recurring_payment = Payment.objects.has_pending_recurring_payment(subscription, created_at__gte)
        if has_pending_recurring_payment:
            raise PaymentPendingRecurringError(subscription.id)
