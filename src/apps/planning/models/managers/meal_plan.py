from datetime import date
from typing import TYPE_CHECKING

from django.db.models import Prefetch

from core.base.managers import BaseManager, BaseQuerySet

if TYPE_CHECKING:
    from apps.planning.models import MealPlanItem  # noqa: F401
    from apps.users.models import User


class MealPlanItemQuerySet(BaseQuerySet['MealPlanItem']):
    def for_user(self, user: User) -> MealPlanItemQuerySet:
        return self.filter(owner=user)

    def with_dish(self) -> MealPlanItemQuerySet:
        return self.select_related('dish')

    def with_dish_category(self) -> MealPlanItemQuerySet:
        return self.select_related('dish__category')

    def prefetch_dish_ingredients_full(self) -> MealPlanItemQuerySet:
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

    def with_with_cooking_event(self) -> MealPlanItemQuerySet:
        return self.select_related('cooking_event')

    def with_full_info_for_user(self) -> MealPlanItemQuerySet:
        return self.with_dish().with_dish_category().with_with_cooking_event().prefetch_dish_ingredients_full()


class MealPlanItemManager(BaseManager['MealPlanItem', MealPlanItemQuerySet]):
    def get_queryset_class(self) -> type[MealPlanItemQuerySet]:
        return MealPlanItemQuerySet

    def for_user(self, user: User) -> MealPlanItemQuerySet:
        return self.get_queryset().for_user(user)

    def full_info_for_user(self, user: User) -> MealPlanItemQuerySet:
        return self.for_user(user).with_full_info_for_user()

    def get_for_user_and_date_range(
        self, user: User, start_date: str | date, end_date: str | date
    ) -> MealPlanItemQuerySet:
        return self.get_queryset().for_user(user).filter(date__range=(start_date, end_date))

    def get_for_week(self, user: User, start_week: str | date, end_week: str | date) -> MealPlanItemQuerySet:
        return self.get_for_user_and_date_range(user, start_week, end_week).with_dish().with_dish_category()
