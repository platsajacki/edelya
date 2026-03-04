from typing import TYPE_CHECKING

from django.db.models import Q

from core.base.managers import ActiveManager, ActiveQuerySet

if TYPE_CHECKING:
    from apps.dishes.models import Ingredient, IngredientCategory  # noqa: F401
    from apps.users.models import User


class IngredientCategoryQueryset(ActiveQuerySet['IngredientCategory']): ...


class IngredientCategoryManager(ActiveManager['IngredientCategory', IngredientCategoryQueryset]):
    def get_queryset_class(self) -> type[IngredientCategoryQueryset]:
        return IngredientCategoryQueryset


class IngredientQueryset(ActiveQuerySet['Ingredient']):
    def for_user(self, user: User) -> IngredientQueryset:
        return self.actived().filter(Q(owner__isnull=True) | Q(owner=user))

    def with_category(self) -> IngredientQueryset:
        return self.select_related('category')


class IngredientManager(ActiveManager['Ingredient', IngredientQueryset]):
    def get_queryset_class(self) -> type[IngredientQueryset]:
        return IngredientQueryset

    def for_user(self, user: User) -> IngredientQueryset:
        return self.get_queryset().for_user(user).with_category()

    def with_category(self) -> IngredientQueryset:
        return self.get_queryset().with_category()
