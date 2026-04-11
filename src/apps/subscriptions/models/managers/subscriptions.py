from typing import TYPE_CHECKING

from apps.subscriptions.models.model_enums import SubscriptionStatus
from core.base.managers import BaseManager, BaseQuerySet

if TYPE_CHECKING:
    from apps.subscriptions.models import Subscription  # noqa: F401
    from apps.users.models import User


class SubscriptionQuerySet(BaseQuerySet['Subscription']):
    def for_user(self, user: User) -> SubscriptionQuerySet:
        return self.filter(user=user)

    def with_tariff(self) -> SubscriptionQuerySet:
        return self.select_related('tariff')

    def with_user(self) -> SubscriptionQuerySet:
        return self.select_related('user')

    def by_status(self, status: SubscriptionStatus) -> SubscriptionQuerySet:
        return self.filter(status=status)


class SubscriptionManager(BaseManager['Subscription', SubscriptionQuerySet]):
    def get_queryset_class(self) -> type[SubscriptionQuerySet]:
        return SubscriptionQuerySet

    def for_user(self, user: User) -> SubscriptionQuerySet:
        return self.get_queryset().for_user(user)

    def with_tariff(self) -> SubscriptionQuerySet:
        return self.get_queryset().with_tariff()

    def for_user_with_tariff(self, user: User) -> SubscriptionQuerySet:
        return self.get_queryset().for_user(user).with_tariff()
