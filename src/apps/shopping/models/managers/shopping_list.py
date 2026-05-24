from typing import TYPE_CHECKING
from uuid import UUID

from core.base.managers import BaseManager, BaseQuerySet

if TYPE_CHECKING:
    from apps.shopping.models.shopping_list import ShoppingList, ShoppingListItem  # noqa: F401
    from apps.users.models import User


class ShoppingListQuerySet(BaseQuerySet['ShoppingList']):
    def for_user(self, user: User) -> ShoppingListQuerySet:
        return self.filter(owner=user)

    def with_items(self) -> ShoppingListQuerySet:
        return self.prefetch_related('items')


class ShoppingListManager(BaseManager['ShoppingList', ShoppingListQuerySet]):
    def get_queryset_class(self) -> type[ShoppingListQuerySet]:
        return ShoppingListQuerySet

    def for_user(self, user: User) -> ShoppingListQuerySet:
        return self.get_queryset().for_user(user)

    def with_items(self) -> ShoppingListQuerySet:
        return self.get_queryset().with_items()


class ShoppingListItemQuerySet(BaseQuerySet['ShoppingListItem']):
    def for_user(self, user: User) -> ShoppingListItemQuerySet:
        return self.filter(owner=user)

    def for_shopping_list(self, shopping_list: ShoppingList | str | UUID) -> ShoppingListItemQuerySet:
        if isinstance(shopping_list, (str, UUID)):
            return self.filter(shopping_list_id=shopping_list)  # type: ignore[misc]
        return self.filter(shopping_list=shopping_list)

    def with_ingredient(self) -> ShoppingListItemQuerySet:
        return self.select_related('ingredient')

    def with_ingredient_and_ingredient_category(self) -> ShoppingListItemQuerySet:
        return self.with_ingredient().select_related('ingredient__category')

    def with_shopping_list(self) -> ShoppingListItemQuerySet:
        return self.select_related('shopping_list')


class ShoppingListItemManager(BaseManager['ShoppingListItem', ShoppingListItemQuerySet]):
    def get_queryset_class(self) -> type[ShoppingListItemQuerySet]:
        return ShoppingListItemQuerySet

    def for_user(self, user: User) -> ShoppingListItemQuerySet:
        return self.get_queryset().for_user(user)

    def for_shopping_list(self, shopping_list: ShoppingList | str | UUID) -> ShoppingListItemQuerySet:
        return self.get_queryset().for_shopping_list(shopping_list)

    def for_user_and_shopping_list(
        self, user: User, shopping_list: ShoppingList | str | UUID
    ) -> ShoppingListItemQuerySet:
        return self.get_queryset().for_user(user).for_shopping_list(shopping_list)

    def with_ingredient(self) -> ShoppingListItemQuerySet:
        return self.get_queryset().with_ingredient()

    def for_user_and_shopping_list_with_related(
        self, user: User, shopping_list: ShoppingList | str | UUID
    ) -> ShoppingListItemQuerySet:
        return self.for_user_and_shopping_list(user, shopping_list).with_ingredient_and_ingredient_category()
