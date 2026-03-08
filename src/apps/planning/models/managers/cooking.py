from datetime import date
from typing import TYPE_CHECKING

from core.base.managers import BaseManager, BaseQuerySet

if TYPE_CHECKING:
    from apps.planning.models import CookingEvent  # noqa: F401
    from apps.users.models import User


class CookingEventQuerySet(BaseQuerySet['CookingEvent']):
    def for_user(self, user: User) -> CookingEventQuerySet:
        return self.filter(owner=user)

    def with_dish(self) -> CookingEventQuerySet:
        return self.select_related('dish')

    def with_dish_category(self) -> CookingEventQuerySet:
        return self.select_related('dish__category')


class CookingEventManager(BaseManager['CookingEvent', CookingEventQuerySet]):
    def get_queryset_class(self) -> type[CookingEventQuerySet]:
        return CookingEventQuerySet

    def for_user(self, user: User) -> CookingEventQuerySet:
        return self.get_queryset().for_user(user)

    def get_for_user_and_date_range(
        self, user: User, start_date: str | date, end_date: str | date
    ) -> CookingEventQuerySet:
        return self.get_queryset().for_user(user).filter(cooking_date__range=(start_date, end_date))

    def get_for_week(self, user: User, start_week: str | date, end_week: str | date) -> CookingEventQuerySet:
        return self.get_for_user_and_date_range(user, start_week, end_week).with_dish().with_dish_category()
