from datetime import timedelta
from typing import TYPE_CHECKING

from django.utils import timezone

from apps.subscriptions.constants import CHECK_SUBSCRIPTION_PAYMENT_TIMEDELTA, GRACE_PERIOD_DAYS
from apps.subscriptions.models.model_enums import SubscriptionStatus
from core.base.managers import BaseManager, BaseQuerySet

if TYPE_CHECKING:
    from apps.subscriptions.models import Subscription  # noqa: F401
    from apps.users.models import User


class SubscriptionQuerySet(BaseQuerySet['Subscription']):
    def for_user(self, user: User) -> SubscriptionQuerySet:
        return self.filter(user=user)

    def with_tariff(self) -> SubscriptionQuerySet:
        return self.select_related('tariff', 'pending_tariff')

    def with_user(self) -> SubscriptionQuerySet:
        return self.select_related('user')

    def by_status(self, status: SubscriptionStatus) -> SubscriptionQuerySet:
        return self.filter(status=status)

    def trials(self) -> SubscriptionQuerySet:
        return self.by_status(SubscriptionStatus.TRIAL)

    def get_trial_to_paid(self) -> SubscriptionQuerySet:
        """Триальные подписки с истёкшим пробным периодом и готовые к оплате."""
        trial_ended_at__lte = timezone.now() + CHECK_SUBSCRIPTION_PAYMENT_TIMEDELTA
        return (
            self.trials()
            .filter(
                trial_ended_at__lte=trial_ended_at__lte,
                pending_tariff__isnull=False,
                payment_method__isnull=False,
            )
            .select_related('pending_tariff', 'payment_method', 'user')
        )

    def get_renewals(self) -> SubscriptionQuerySet:
        """Активные подписки с auto_renew=True, у которых заканчивается текущий период."""
        current_period_end__lte = timezone.now() + CHECK_SUBSCRIPTION_PAYMENT_TIMEDELTA
        return self.filter(
            status=SubscriptionStatus.ACTIVE,
            current_period_end__lte=current_period_end__lte,
            auto_renew=True,
            payment_method__isnull=False,
        ).select_related('tariff', 'pending_tariff', 'payment_method', 'user')

    def get_past_due_for_retry(self) -> SubscriptionQuerySet:
        """PAST_DUE подписки, у которых grace period истекает — вторая и последняя попытка списания."""
        current_period_start__lte = (
            timezone.now() + CHECK_SUBSCRIPTION_PAYMENT_TIMEDELTA - timedelta(days=GRACE_PERIOD_DAYS)
        )
        return self.filter(
            status=SubscriptionStatus.PAST_DUE,
            current_period_start__lte=current_period_start__lte,
            payment_method__isnull=False,
        ).select_related('tariff', 'pending_tariff', 'payment_method', 'user')

    def get_abandoned_trials(self) -> SubscriptionQuerySet:
        """Триальные подписки без pending_tariff с истёкшим триалом — никогда не перейдут в ACTIVE."""
        return self.filter(
            status=SubscriptionStatus.TRIAL,
            trial_ended_at__lte=timezone.now(),
            pending_tariff__isnull=True,
        )

    def get_past_due_for_expiry(self) -> SubscriptionQuerySet:
        """PAST_DUE подписки, у которых grace period уже истёк и повторное списание не помогло."""
        grace_deadline = timezone.now() - timedelta(days=GRACE_PERIOD_DAYS)
        return self.filter(
            status=SubscriptionStatus.PAST_DUE,
            current_period_start__lte=grace_deadline,
        )

    def get_cancelled_for_expiry(self) -> SubscriptionQuerySet:
        """Активные подписки с auto_renew=False, у которых истёк оплаченный период."""
        return self.filter(
            status=SubscriptionStatus.ACTIVE,
            auto_renew=False,
            current_period_end__lte=timezone.now(),
        )


class SubscriptionManager(BaseManager['Subscription', SubscriptionQuerySet]):
    def get_queryset_class(self) -> type[SubscriptionQuerySet]:
        return SubscriptionQuerySet

    def for_user(self, user: User) -> SubscriptionQuerySet:
        return self.get_queryset().for_user(user)

    def with_tariff(self) -> SubscriptionQuerySet:
        return self.get_queryset().with_tariff()

    def for_user_with_tariff(self, user: User) -> SubscriptionQuerySet:
        return self.get_queryset().for_user(user).with_tariff()

    def trials(self) -> SubscriptionQuerySet:
        return self.get_queryset().trials()

    def get_trial_to_paid(self) -> SubscriptionQuerySet:
        """Триальные подписки с истёкшим пробным периодом и готовые к оплате."""
        return self.get_queryset().get_trial_to_paid()

    def get_renewals(self) -> SubscriptionQuerySet:
        """Активные подписки с auto_renew=True, у которых заканчивается текущий период."""
        return self.get_queryset().get_renewals()

    def get_past_due_for_retry(self) -> SubscriptionQuerySet:
        """PAST_DUE подписки, у которых grace period истекает — вторая и последняя попытка списания."""
        return self.get_queryset().get_past_due_for_retry()

    def get_abandoned_trials(self) -> SubscriptionQuerySet:
        """Триальные подписки без pending_tariff с истёкшим триалом — никогда не перейдут в ACTIVE."""
        return self.get_queryset().get_abandoned_trials()

    def get_past_due_for_expiry(self) -> SubscriptionQuerySet:
        """PAST_DUE подписки, у которых grace period уже истёк и повторное списание не помогло."""
        return self.get_queryset().get_past_due_for_expiry()

    def get_cancelled_for_expiry(self) -> SubscriptionQuerySet:
        """Активные подписки с auto_renew=False, у которых истёк оплаченный период."""
        return self.get_queryset().get_cancelled_for_expiry()
