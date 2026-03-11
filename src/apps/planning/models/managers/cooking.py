from datetime import date
from typing import TYPE_CHECKING

from django.db.models import Prefetch

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

    def prefetch_dish_ingredients_full(self) -> CookingEventQuerySet:
        return self.prefetch_related(
            Prefetch(
                'dish__dish_ingredients',
                queryset=self.get_dish_ingredient_model()
                .objects.select_related(
                    'ingredient',
                    'ingredient__category',
                )
                .order_by('position', 'created_at'),
            )
        )

    def with_meal_plan_items(self) -> CookingEventQuerySet:
        return self.prefetch_related(
            Prefetch(
                'meal_plan_items',
                queryset=self.get_meal_plan_item_model().objects.order_by('date', 'position', 'created_at'),
            )
        )

    def with_full_info(self) -> CookingEventQuerySet:
        return self.with_dish().with_dish_category().with_meal_plan_items().prefetch_dish_ingredients_full()


class CookingEventManager(BaseManager['CookingEvent', CookingEventQuerySet]):
    def get_queryset_class(self) -> type[CookingEventQuerySet]:
        return CookingEventQuerySet

    def for_user(self, user: User) -> CookingEventQuerySet:
        return self.get_queryset().for_user(user)

    def full_info_for_user(self, user: User) -> CookingEventQuerySet:
        return self.for_user(user).with_full_info()

    def get_for_user_and_date_range(
        self, user: User, start_date: str | date, end_date: str | date
    ) -> CookingEventQuerySet:
        return self.get_queryset().for_user(user).filter(cooking_date__range=(start_date, end_date))

    def get_for_week(self, user: User, start_week: str | date, end_week: str | date) -> CookingEventQuerySet:
        return self.get_for_user_and_date_range(user, start_week, end_week).with_dish().with_dish_category()
