import pytest
from pytest_mock import MockFixture

from datetime import date
from decimal import Decimal
from uuid import uuid4

from apps.dishes.models import Dish, Ingredient
from apps.planning.models import CookingEvent
from apps.shopping.api.services.shopping_list_recalculater import (
    ShoppingListInstanceRecalculater,
    ShoppingListRecalculater,
)
from apps.shopping.data_types import IngredientTotalAmountData
from apps.shopping.models import ShoppingList, ShoppingListItem
from apps.users.models import User


class TestShoppingListRecalculaterGetItems:
    def test_returns_empty_dict_when_no_items(self, shopping_list: ShoppingList) -> None:
        result = ShoppingListRecalculater().get_items(shopping_list)
        assert result == {}

    def test_includes_non_manual_items_keyed_by_ingredient_id(
        self,
        shopping_list: ShoppingList,
        shopping_list_item: ShoppingListItem,
    ) -> None:
        result = ShoppingListRecalculater().get_items(shopping_list)
        assert shopping_list_item.ingredient_id in result
        assert result[shopping_list_item.ingredient_id] == shopping_list_item

    def test_excludes_manual_items(
        self,
        shopping_list: ShoppingList,
        manual_shopping_list_item: ShoppingListItem,
    ) -> None:
        result = ShoppingListRecalculater().get_items(shopping_list)
        assert manual_shopping_list_item.ingredient_id not in result

    def test_returns_only_non_manual_when_both_types_exist(
        self,
        shopping_list: ShoppingList,
        shopping_list_item: ShoppingListItem,
        manual_shopping_list_item: ShoppingListItem,
    ) -> None:
        result = ShoppingListRecalculater().get_items(shopping_list)
        assert shopping_list_item.ingredient_id in result
        assert manual_shopping_list_item.ingredient_id not in result
        assert len(result) == 1


class TestShoppingListRecalculaterProcessExistingItem:
    def test_different_amount_updates_item_and_appends_to_update(self) -> None:
        item = ShoppingListItem(amount=Decimal('50.000'))
        ingredient_data: IngredientTotalAmountData = {
            'ingredient_id': uuid4(),
            'ingredient__base_unit': 'gram',
            'total_amount': Decimal('100.000'),
        }
        to_update: list[ShoppingListItem] = []
        ShoppingListRecalculater().process_existing_item(ingredient_data, item, to_update)
        assert item.amount == Decimal('100.000')
        assert item in to_update

    def test_same_amount_does_not_append_to_update(self) -> None:
        item = ShoppingListItem(amount=Decimal('100.000'))
        ingredient_data: IngredientTotalAmountData = {
            'ingredient_id': uuid4(),
            'ingredient__base_unit': 'gram',
            'total_amount': Decimal('100.000'),
        }
        to_update: list[ShoppingListItem] = []
        ShoppingListRecalculater().process_existing_item(ingredient_data, item, to_update)
        assert len(to_update) == 0


class TestShoppingListRecalculaterProcessNewItem:
    def test_appends_new_item_with_correct_fields(self, shopping_list: ShoppingList) -> None:
        ingredient_id = uuid4()
        ingredient_data: IngredientTotalAmountData = {
            'ingredient_id': ingredient_id,
            'ingredient__base_unit': 'gram',
            'total_amount': Decimal('150.000'),
        }
        to_create: list[ShoppingListItem] = []
        ShoppingListRecalculater().process_new_item(shopping_list, ingredient_data, to_create)
        assert len(to_create) == 1
        item = to_create[0]
        assert item.shopping_list == shopping_list
        assert item.owner == shopping_list.owner
        assert item.ingredient_id == ingredient_id
        assert item.amount == Decimal('150.000')


class TestShoppingListRecalculaterProcessDeletedItems:
    def test_item_absent_from_ingredients_data_goes_to_delete(
        self,
        ingredient_global: Ingredient,
    ) -> None:
        item = ShoppingListItem(ingredient_id=ingredient_global.id)
        actual_items_dict = {ingredient_global.id: item}
        to_delete: list[ShoppingListItem] = []
        ShoppingListRecalculater().process_deleted_items([], actual_items_dict, to_delete)
        assert item in to_delete

    def test_item_present_in_ingredients_data_is_not_deleted(
        self,
        ingredient_global: Ingredient,
    ) -> None:
        item = ShoppingListItem(ingredient_id=ingredient_global.id)
        actual_items_dict = {ingredient_global.id: item}
        ingredients_data: list[IngredientTotalAmountData] = [
            {
                'ingredient_id': ingredient_global.id,
                'ingredient__base_unit': 'gram',
                'total_amount': Decimal('100.000'),
            }
        ]
        to_delete: list[ShoppingListItem] = []
        ShoppingListRecalculater().process_deleted_items(ingredients_data, actual_items_dict, to_delete)
        assert len(to_delete) == 0

    def test_empty_ingredients_data_moves_all_items_to_delete(
        self,
        ingredient_global: Ingredient,
        ingredient_user: Ingredient,
    ) -> None:
        item1 = ShoppingListItem(ingredient_id=ingredient_global.id)
        item2 = ShoppingListItem(ingredient_id=ingredient_user.id)
        actual_items_dict = {ingredient_global.id: item1, ingredient_user.id: item2}
        to_delete: list[ShoppingListItem] = []
        ShoppingListRecalculater().process_deleted_items([], actual_items_dict, to_delete)
        assert item1 in to_delete
        assert item2 in to_delete


class TestShoppingListRecalculaterGetIngredientsForDateRange:
    def test_returns_empty_when_no_cooking_events(self, shopping_list: ShoppingList) -> None:
        result = list(ShoppingListRecalculater().get_ingredients_for_date_range(shopping_list))
        assert result == []

    def test_returns_ingredient_for_event_in_range(
        self,
        shopping_list: ShoppingList,
        cooking_event_with_ingredients: CookingEvent,
        ingredient_global: Ingredient,
    ) -> None:
        result = list(ShoppingListRecalculater().get_ingredients_for_date_range(shopping_list))
        assert len(result) == 1
        assert result[0]['ingredient_id'] == ingredient_global.id
        assert result[0]['total_amount'] == Decimal('100.000')

    def test_excludes_event_outside_date_range(
        self,
        shopping_list: ShoppingList,
        cooking_event_outside_range: CookingEvent,
    ) -> None:
        result = list(ShoppingListRecalculater().get_ingredients_for_date_range(shopping_list))
        assert result == []

    def test_excludes_other_user_cooking_events(
        self,
        shopping_list: ShoppingList,
        another_telegram_user: User,
        dish_user_with_ingredient: Dish,
        week_start: date,
    ) -> None:
        CookingEvent.objects.create(
            owner=another_telegram_user,
            dish=dish_user_with_ingredient,
            cooking_date=week_start,
        )
        result = list(ShoppingListRecalculater().get_ingredients_for_date_range(shopping_list))
        assert result == []

    def test_includes_event_on_date_from_boundary(
        self,
        shopping_list: ShoppingList,
        telegram_user: User,
        dish_user_with_ingredient: Dish,
        week_start: date,
    ) -> None:
        CookingEvent.objects.create(
            owner=telegram_user,
            dish=dish_user_with_ingredient,
            cooking_date=week_start,  # == date_from
        )
        result = list(ShoppingListRecalculater().get_ingredients_for_date_range(shopping_list))
        assert len(result) == 1

    def test_includes_event_on_date_to_boundary(
        self,
        shopping_list: ShoppingList,
        telegram_user: User,
        dish_user_with_ingredient: Dish,
        week_end: date,
    ) -> None:
        CookingEvent.objects.create(
            owner=telegram_user,
            dish=dish_user_with_ingredient,
            cooking_date=week_end,  # == date_to
        )
        result = list(ShoppingListRecalculater().get_ingredients_for_date_range(shopping_list))
        assert len(result) == 1

    def test_sums_amounts_for_same_ingredient_across_multiple_events(
        self,
        shopping_list: ShoppingList,
        cooking_event_with_ingredients: CookingEvent,
        second_cooking_event_with_same_ingredient: CookingEvent,
        ingredient_global: Ingredient,
    ) -> None:
        result = list(ShoppingListRecalculater().get_ingredients_for_date_range(shopping_list))
        assert len(result) == 1
        assert result[0]['ingredient_id'] == ingredient_global.id
        assert result[0]['total_amount'] == Decimal('200.000')


class TestShoppingListRecalculaterRecalculate:
    def test_creates_items_for_all_ingredients_in_range(
        self,
        shopping_list: ShoppingList,
        cooking_event_with_ingredients: CookingEvent,
        ingredient_global: Ingredient,
    ) -> None:
        ShoppingListRecalculater().recalculate_shopping_list_items(shopping_list)
        items = ShoppingListItem.objects.filter(shopping_list=shopping_list, is_manual=False)
        assert items.count() == 1
        item = items.first()
        assert item is not None
        assert item.ingredient_id == ingredient_global.id
        assert item.amount == Decimal('100.000')
        assert item.owner == shopping_list.owner

    def test_updates_existing_item_when_amount_changed(
        self,
        shopping_list: ShoppingList,
        ingredient_global: Ingredient,
        cooking_event_with_ingredients: CookingEvent,
    ) -> None:
        item = ShoppingListItem.objects.create(
            shopping_list=shopping_list,
            owner=shopping_list.owner,
            ingredient=ingredient_global,
            amount=Decimal('50.000'),  # stale — differs from cooking event (100.000)
            is_manual=False,
        )
        ShoppingListRecalculater().recalculate_shopping_list_items(shopping_list)
        item.refresh_from_db()
        assert item.amount == Decimal('100.000')

    def test_does_not_call_bulk_update_when_amount_unchanged(
        self,
        shopping_list: ShoppingList,
        shopping_list_item: ShoppingListItem,  # amount=100, not manual
        cooking_event_with_ingredients: CookingEvent,  # dish ingredient amount=100
        mocker: MockFixture,
    ) -> None:
        spy = mocker.spy(ShoppingListItem.objects, 'bulk_update')
        ShoppingListRecalculater().recalculate_shopping_list_items(shopping_list)
        spy.assert_not_called()

    def test_deletes_non_manual_item_absent_from_range(
        self,
        shopping_list: ShoppingList,
        shopping_list_item: ShoppingListItem,  # no cooking events → this item must be deleted
    ) -> None:
        ShoppingListRecalculater().recalculate_shopping_list_items(shopping_list)
        assert not ShoppingListItem.objects.filter(id=shopping_list_item.id).exists()

    def test_no_items_created_when_no_cooking_events(
        self,
        shopping_list: ShoppingList,
    ) -> None:
        ShoppingListRecalculater().recalculate_shopping_list_items(shopping_list)
        assert not ShoppingListItem.objects.filter(shopping_list=shopping_list).exists()

    def test_preserves_manual_item_when_no_cooking_events(
        self,
        shopping_list: ShoppingList,
        manual_shopping_list_item: ShoppingListItem,
    ) -> None:
        ShoppingListRecalculater().recalculate_shopping_list_items(shopping_list)
        assert ShoppingListItem.objects.filter(id=manual_shopping_list_item.id).exists()

    def test_preserves_manual_item_while_creating_non_manual_for_same_ingredient(
        self,
        shopping_list: ShoppingList,
        ingredient_global: Ingredient,
        cooking_event_with_ingredients: CookingEvent,
    ) -> None:
        manual = ShoppingListItem.objects.create(
            shopping_list=shopping_list,
            owner=shopping_list.owner,
            ingredient=ingredient_global,
            amount=Decimal('999.000'),
            is_manual=True,
        )
        ShoppingListRecalculater().recalculate_shopping_list_items(shopping_list)
        manual.refresh_from_db()
        assert manual.amount == Decimal('999.000')
        assert manual.is_manual is True
        assert ShoppingListItem.objects.filter(
            shopping_list=shopping_list,
            ingredient=ingredient_global,
            is_manual=False,
        ).exists()

    def test_sums_amounts_from_multiple_events_for_same_ingredient(
        self,
        shopping_list: ShoppingList,
        cooking_event_with_ingredients: CookingEvent,
        second_cooking_event_with_same_ingredient: CookingEvent,
        ingredient_global: Ingredient,
    ) -> None:
        ShoppingListRecalculater().recalculate_shopping_list_items(shopping_list)
        item = ShoppingListItem.objects.get(
            shopping_list=shopping_list,
            ingredient=ingredient_global,
            is_manual=False,
        )
        assert item.amount == Decimal('200.000')

    def test_excludes_other_user_cooking_events(
        self,
        shopping_list: ShoppingList,
        another_telegram_user: User,
        dish_user_with_ingredient: Dish,
        week_start: date,
    ) -> None:
        CookingEvent.objects.create(
            owner=another_telegram_user,
            dish=dish_user_with_ingredient,
            cooking_date=week_start,
        )
        ShoppingListRecalculater().recalculate_shopping_list_items(shopping_list)
        assert not ShoppingListItem.objects.filter(shopping_list=shopping_list, is_manual=False).exists()


class TestShoppingListInstanceRecalculater:
    def test_act_recalculates_items_and_returns_instance(
        self,
        shopping_list: ShoppingList,
        cooking_event_with_ingredients: CookingEvent,
        ingredient_global: Ingredient,
    ) -> None:
        svc = ShoppingListInstanceRecalculater(instance=shopping_list)
        result = svc()
        assert result is shopping_list
        assert ShoppingListItem.objects.filter(shopping_list=shopping_list, is_manual=False).count() == 1

    def test_act_rolls_back_on_error(
        self,
        shopping_list: ShoppingList,
        cooking_event_with_ingredients: CookingEvent,
        mocker: MockFixture,
    ) -> None:
        """Items created inside recalculate must be rolled back if any error follows."""
        original = ShoppingListRecalculater.recalculate_shopping_list_items

        def patched(self_inner: ShoppingListRecalculater, sl: ShoppingList) -> None:
            original(self_inner, sl)
            raise RuntimeError('force rollback')

        mocker.patch.object(ShoppingListRecalculater, 'recalculate_shopping_list_items', patched)
        svc = ShoppingListInstanceRecalculater(instance=shopping_list)
        with pytest.raises(RuntimeError):
            svc()
        assert not ShoppingListItem.objects.filter(shopping_list=shopping_list, is_manual=False).exists()
