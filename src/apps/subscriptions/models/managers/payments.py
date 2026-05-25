from typing import TYPE_CHECKING

from django.db.models import Manager, QuerySet
from django.utils import timezone

from apps.subscriptions.constants import CHECK_SUBSCRIPTION_PAYMENT_TIMEDELTA, ZERO_AMOUNT_BINDING_EXPIRY
from apps.subscriptions.models.model_enums import PaymentStatus, PaymentType

if TYPE_CHECKING:
    from apps.subscriptions.models import Payment, Subscription  # noqa: F401


class PaymentQuerySet(QuerySet['Payment']):
    def get_pending_recurring_payments(self, subscription: Subscription) -> PaymentQuerySet:
        created_at__gte = timezone.now() - CHECK_SUBSCRIPTION_PAYMENT_TIMEDELTA
        return self.filter(
            subscription=subscription,
            status=PaymentStatus.PENDING,
            payment_type=PaymentType.RECURRING,
            created_at__gte=created_at__gte,
        )

    def to_send_check(self) -> PaymentQuerySet:
        return self.filter(send_to_tax3r=True, is_check_sent=False)

    def get_stale_zero_amount_bindings(self) -> PaymentQuerySet:
        expiry_threshold = timezone.now() - ZERO_AMOUNT_BINDING_EXPIRY
        return self.filter(
            payment_type=PaymentType.ZERO_AMOUNT_BINDING,
            status=PaymentStatus.PENDING,
            created_at__lt=expiry_threshold,
        )


class PaymentManager(Manager['Payment']):
    def get_queryset(self) -> PaymentQuerySet:
        return PaymentQuerySet(self.model, using=self._db)

    def get_pending_recurring_payments(self, subscription: Subscription) -> PaymentQuerySet:
        return self.get_queryset().get_pending_recurring_payments(subscription)

    def has_pending_recurring_payment(self, subscription: Subscription) -> bool:
        return self.get_pending_recurring_payments(subscription).exists()

    def to_send_check(self) -> PaymentQuerySet:
        return self.get_queryset().to_send_check()

    def get_stale_zero_amount_bindings(self) -> PaymentQuerySet:
        return self.get_queryset().get_stale_zero_amount_bindings()
