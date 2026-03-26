import pytest

from decimal import Decimal

from _tests import FixtureFactory
from apps.dishes.models import Dish, DishCategory, DishIngredient
from apps.dishes.models.ingredients import Ingredient
from apps.users.models import User


@pytest.fixture
def dish_category_data(factory: FixtureFactory) -> list[dict]:
    return factory.schema(
        lambda: {'name': factory.generic.text.word()},
        iterations=10,
    ).create()


@pytest.fixture
def dish_category(dish_category_data: list[dict]) -> DishCategory:
    data = dish_category_data[0]
    return DishCategory.objects.create(**data)


@pytest.fixture
def second_dish_category(dish_category_data: list[dict]) -> DishCategory:
    data = dish_category_data[1]
    return DishCategory.objects.create(**data)


@pytest.fixture
def dish_categories(dish_category_data: list[dict]) -> list[DishCategory]:
    bulk_data = [DishCategory(**data) for data in dish_category_data[5::]]
    return DishCategory.objects.bulk_create(bulk_data)


@pytest.fixture
def dish_data(factory: FixtureFactory, dish_category: DishCategory) -> list[dict]:
    return factory.schema(
        lambda: {
            'name': factory.generic.text.word(),
            'owner': None,
            'category': dish_category,
            'recipe': '',
        },
        iterations=10,
    ).create()


@pytest.fixture
def dish_global(dish_data: list[dict]) -> Dish:
    data = dish_data[0]
    return Dish.objects.create(**data)


@pytest.fixture
def dish_user(dish_data: list[dict], telegram_user: User) -> Dish:
    data = dish_data[1]
    data['owner'] = telegram_user
    return Dish.objects.create(**data)


@pytest.fixture
def dishes(dish_data: list[dict]) -> list[Dish]:
    bulk_data = [Dish(**data) for data in dish_data[5::]]
    return Dish.objects.bulk_create(bulk_data)


@pytest.fixture
def dish_user_with_ingredient(dish_user: Dish, ingredient_global: Ingredient) -> Dish:
    DishIngredient.objects.create(
        dish=dish_user,
        ingredient=ingredient_global,
        amount=Decimal('100.000'),
        is_optional=False,
    )
    return dish_user
