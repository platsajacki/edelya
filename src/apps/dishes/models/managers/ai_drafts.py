from typing import TYPE_CHECKING

from django.db.models import Q

from apps.subscriptions.constants import AI_RECIPE_LIMIT_PER_PERIOD
from core.base.managers import BaseManager, BaseQuerySet

if TYPE_CHECKING:
    from apps.dishes.models import DishAIDraft  # noqa: F401
    from apps.subscriptions.models import Subscription
    from apps.users.models import User


class DishAIDraftQueryset(BaseQuerySet['DishAIDraft']):
    def for_user(self, user: User) -> DishAIDraftQueryset:
        return self.filter(owner=user)

    def filter_by_subscription_period(self, subscription: Subscription) -> DishAIDraftQueryset | None:
        if subscription.started_at is None or subscription.ended_at is None:
            return None
        return self.filter(
            Q(owner=subscription.user)
            & Q(created_at__gte=subscription.started_at)
            & Q(created_at__lte=subscription.ended_at)
        )

    def count_by_subscription_period(self, subscription: Subscription) -> int:
        qs = self.filter_by_subscription_period(subscription)
        if qs is None:
            return -1
        return qs.count()

    def can_create_new_draft(self, subscription: Subscription) -> bool:
        count = self.count_by_subscription_period(subscription)
        if count == -1:
            return False
        return count < AI_RECIPE_LIMIT_PER_PERIOD


class DishAIDraftManager(BaseManager['DishAIDraft', DishAIDraftQueryset]):
    def get_queryset_class(self) -> type[DishAIDraftQueryset]:
        return DishAIDraftQueryset

    def for_user(self, user: User) -> DishAIDraftQueryset:
        return self.get_queryset().for_user(user)

    def filter_by_subscription_period(self, subscription: Subscription) -> DishAIDraftQueryset | None:
        return self.get_queryset().filter_by_subscription_period(subscription)

    def count_by_subscription_period(self, subscription: Subscription) -> int:
        return self.get_queryset().count_by_subscription_period(subscription)

    def can_create_new_draft(self, subscription: Subscription) -> bool:
        return self.get_queryset().can_create_new_draft(subscription)
