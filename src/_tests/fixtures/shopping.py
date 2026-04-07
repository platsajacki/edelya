import pytest

from datetime import date, timedelta
from decimal import Decimal

from apps.dishes.models import Dish, Ingredient
from apps.planning.models import CookingEvent
from apps.shopping.models import ShoppingList, ShoppingListItem
from apps.users.models import User


@pytest.fixture
def shopping_list(telegram_user: User, week_start: date, week_end: date) -> ShoppingList:
    return ShoppingList.objects.create(
        name='Test Shopping List',
        owner=telegram_user,
        date_from=week_start,
        date_to=week_end,
    )


@pytest.fixture
def shopping_list_item(shopping_list: ShoppingList, ingredient_global: Ingredient) -> ShoppingListItem:
    """Non-manual item for ingredient_global with amount=100."""
    return ShoppingListItem.objects.create(
        shopping_list=shopping_list,
        owner=shopping_list.owner,
        ingredient=ingredient_global,
        amount=Decimal('100.000'),
        is_manual=False,
    )


@pytest.fixture
def manual_shopping_list_item(shopping_list: ShoppingList, ingredient_user: Ingredient) -> ShoppingListItem:
    """Manual item for ingredient_user (different ingredient than shopping_list_item)."""
    return ShoppingListItem.objects.create(
        shopping_list=shopping_list,
        owner=shopping_list.owner,
        ingredient=ingredient_user,
        amount=Decimal('50.000'),
        manual_amount=Decimal('50.000'),
        is_manual=True,
    )


@pytest.fixture
def cooking_event_with_ingredients(
    telegram_user: User,
    dish_user_with_ingredient: Dish,
    week_start: date,
) -> CookingEvent:
    """CookingEvent in range for telegram_user; dish has ingredient_global with amount=100."""
    return CookingEvent.objects.create(
        owner=telegram_user,
        dish=dish_user_with_ingredient,
        cooking_date=week_start,
    )


@pytest.fixture
def second_cooking_event_with_same_ingredient(
    telegram_user: User,
    dish_user_with_ingredient: Dish,
    week_start: date,
) -> CookingEvent:
    """Second CookingEvent for the same dish in range — used to verify Sum aggregation."""
    return CookingEvent.objects.create(
        owner=telegram_user,
        dish=dish_user_with_ingredient,
        cooking_date=week_start + timedelta(days=1),
    )


@pytest.fixture
def cooking_event_outside_range(
    telegram_user: User,
    dish_user_with_ingredient: Dish,
    week_end: date,
) -> CookingEvent:
    """CookingEvent one day AFTER week_end — must not appear in recalculation."""
    return CookingEvent.objects.create(
        owner=telegram_user,
        dish=dish_user_with_ingredient,
        cooking_date=week_end + timedelta(days=1),
    )
