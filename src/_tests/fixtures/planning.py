import pytest

from datetime import date

from apps.dishes.models import Dish
from apps.planning.models import CookingEvent, MealPlanItem
from apps.users.models import User

WEEK_YEAR = 2026
WEEK_NUMBER = 10
# ISO week 10 of 2026: Mon 2026-03-02 – Sun 2026-03-08
WEEK_START = date(2026, 3, 2)
WEEK_END = date(2026, 3, 8)


@pytest.fixture
def week_year() -> int:
    return WEEK_YEAR


@pytest.fixture
def week_number() -> int:
    return WEEK_NUMBER


@pytest.fixture
def week_start() -> date:
    return WEEK_START


@pytest.fixture
def week_end() -> date:
    return WEEK_END


@pytest.fixture
def cooking_event(telegram_user: User, dish_global: Dish) -> CookingEvent:
    return CookingEvent.objects.create(
        owner=telegram_user,
        dish=dish_global,
        cooking_date=WEEK_START,
        duration_days=3,
        start_eating_date=WEEK_START,
        notes='',
    )


@pytest.fixture
def another_user_cooking_event(another_telegram_user: User, dish_global: Dish) -> CookingEvent:
    return CookingEvent.objects.create(
        owner=another_telegram_user,
        dish=dish_global,
        cooking_date=WEEK_START,
        duration_days=1,
        start_eating_date=WEEK_START,
        notes='',
    )


@pytest.fixture
def meal_plan_item(telegram_user: User, dish_global: Dish) -> MealPlanItem:
    return MealPlanItem.objects.create(
        owner=telegram_user,
        dish=dish_global,
        date=WEEK_START,
        position=1,
        is_manual=True,
    )


@pytest.fixture
def another_user_meal_plan_item(another_telegram_user: User, dish_global: Dish) -> MealPlanItem:
    return MealPlanItem.objects.create(
        owner=another_telegram_user,
        dish=dish_global,
        date=WEEK_START,
        position=1,
        is_manual=True,
    )
