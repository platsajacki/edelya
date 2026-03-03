import pytest

from _tests import FixtureFactory
from apps.dishes.models import DishCategory


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
