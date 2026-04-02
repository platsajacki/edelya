from uuid import UUID

from django.db import transaction

from apps.dishes.models import DishIngredient
from apps.shopping.data_types import IngredientTotalAmountData
from apps.shopping.models import ShoppingList, ShoppingListItem
from core.base.services import BaseInstanceService, BaseViewSetPerformService


class ShoppingListRecalculater:
    def get_ingredients_for_date_range(self, shopping_list: ShoppingList) -> list[IngredientTotalAmountData]:
        return DishIngredient.objects.get_ingredits_for_shopping_list(shopping_list)

    def process_existing_item(
        self,
        ingredient_data: IngredientTotalAmountData,
        actual_item: ShoppingListItem,
        to_update: list[ShoppingListItem],
    ) -> None:
        if actual_item.amount != ingredient_data['total_amount']:
            actual_item.amount = ingredient_data['total_amount']
            to_update.append(actual_item)

    def process_new_item(
        self,
        shopping_list: ShoppingList,
        ingredient_data: IngredientTotalAmountData,
        to_create: list[ShoppingListItem],
    ) -> None:
        to_create.append(
            ShoppingListItem(
                shopping_list=shopping_list,
                owner=shopping_list.owner,
                ingredient_id=ingredient_data['ingredient_id'],
                amount=ingredient_data['total_amount'],
            )
        )

    def process_deleted_items(
        self,
        ingredients_data: list[IngredientTotalAmountData],
        actual_items_dict: dict[UUID, ShoppingListItem],
        to_delete: list[ShoppingListItem],
    ) -> None:
        ingredient_ids = {ingredient_data['ingredient_id'] for ingredient_data in ingredients_data}
        for ingredient_id in actual_items_dict:
            if ingredient_id not in ingredient_ids:
                to_delete.append(actual_items_dict[ingredient_id])

    def process_ingredients_data(
        self,
        shopping_list: ShoppingList,
        ingredients_data: list[IngredientTotalAmountData],
        actual_items_dict: dict[UUID, ShoppingListItem],
        to_update: list[ShoppingListItem],
        to_create: list[ShoppingListItem],
        to_delete: list[ShoppingListItem],
    ) -> None:
        for ingredient_data in ingredients_data:
            if ingredient_data['ingredient_id'] in actual_items_dict:
                self.process_existing_item(
                    ingredient_data=ingredient_data,
                    actual_item=actual_items_dict[ingredient_data['ingredient_id']],
                    to_update=to_update,
                )
            else:
                self.process_new_item(
                    shopping_list=shopping_list,
                    ingredient_data=ingredient_data,
                    to_create=to_create,
                )
        self.process_deleted_items(
            ingredients_data=ingredients_data,
            actual_items_dict=actual_items_dict,
            to_delete=to_delete,
        )
        if to_update:
            ShoppingListItem.objects.bulk_update(to_update, ['amount'])
        if to_create:
            ShoppingListItem.objects.bulk_create(to_create)
        if to_delete:
            ShoppingListItem.objects.filter(id__in=[item.id for item in to_delete]).delete()

    def get_items(self, shopping_list: ShoppingList) -> dict[UUID, ShoppingListItem]:
        qs = shopping_list.items.filter(is_manual=False)
        return {item.ingredient_id: item for item in qs}

    def recalculate_shopping_list_items(self, shopping_list: ShoppingList) -> None:
        actual_items_dict = self.get_items(shopping_list)
        ingredients_data = self.get_ingredients_for_date_range(shopping_list)
        to_update: list[ShoppingListItem] = []
        to_create: list[ShoppingListItem] = []
        to_delete: list[ShoppingListItem] = []
        self.process_ingredients_data(
            shopping_list=shopping_list,
            ingredients_data=ingredients_data,
            actual_items_dict=actual_items_dict,
            to_update=to_update,
            to_create=to_create,
            to_delete=to_delete,
        )


class ShoppingListPerformRecalculater(BaseViewSetPerformService, ShoppingListRecalculater):
    @transaction.atomic
    def act(self) -> ShoppingList:
        shopping_list: ShoppingList = self.serializer.save()
        self.recalculate_shopping_list_items(shopping_list)
        return shopping_list


class ShoppingListInstanceRecalculater(BaseInstanceService, ShoppingListRecalculater):
    @transaction.atomic
    def act(self) -> ShoppingList:
        if not isinstance(self.instance, ShoppingList):
            raise ValueError('Instance must be a ShoppingList')
        self.recalculate_shopping_list_items(self.instance)
        return self.instance
