from typing import TYPE_CHECKING

from django.db.models import Q

from core.base.managers import ActiveManager, ActiveQuerySet

if TYPE_CHECKING:
    from apps.dishes.models import Dish, DishCategory, DishIngredient  # noqa: F401
    from apps.users.models import User


class DishCategoryQueryset(ActiveQuerySet['DishCategory']): ...


class DishCategoryManager(ActiveManager['DishCategory', DishCategoryQueryset]):
    def get_queryset_class(self) -> type[DishCategoryQueryset]:
        return DishCategoryQueryset


class DishQueryset(ActiveQuerySet['Dish']):
    def for_user(self, user: User) -> DishQueryset:
        return self.actived().filter(Q(owner__isnull=True) | Q(owner=user))

    def with_category(self) -> DishQueryset:
        return self.select_related('category')

    def with_ingredients(self) -> DishQueryset:
        return self.prefetch_related('dish_ingredients__ingredient')


class DishManager(ActiveManager['Dish', DishQueryset]):
    def get_queryset_class(self) -> type[DishQueryset]:
        return DishQueryset

    def for_user(self, user: User) -> DishQueryset:
        return self.get_queryset().for_user(user).with_category().with_ingredients()

    def with_category(self) -> DishQueryset:
        return self.get_queryset().with_category()

    def with_ingredients(self) -> DishQueryset:
        return self.get_queryset().with_ingredients()
