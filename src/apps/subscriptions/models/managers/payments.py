from datetime import datetime
from typing import TYPE_CHECKING

from django.db.models import Manager, QuerySet

from apps.subscriptions.models.model_enums import PaymentStatus, PaymentType

if TYPE_CHECKING:
    from apps.subscriptions.models import Payment, Subscription  # noqa: F401


class PaymentQuerySet(QuerySet['Payment']):
    def get_pending_recurring_payments(self, subscription: Subscription, created_at__gte: datetime) -> PaymentQuerySet:
        return self.filter(
            subscription=subscription,
            status=PaymentStatus.PENDING,
            payment_type=PaymentType.RECURRING,
            created_at__gte=created_at__gte,
        )


class PaymentManager(Manager['Payment']):
    def get_queryset(self) -> PaymentQuerySet:
        return PaymentQuerySet(self.model, using=self._db)

    def get_pending_recurring_payments(self, subscription: Subscription, created_at__gte: datetime) -> PaymentQuerySet:
        return self.get_queryset().get_pending_recurring_payments(subscription, created_at__gte)

    def has_pending_recurring_payment(self, subscription: Subscription, created_at__gte: datetime) -> bool:
        return self.get_pending_recurring_payments(subscription, created_at__gte).exists()
