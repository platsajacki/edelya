import pytest

from _tests import FixtureFactory
from dishes.models import Ingredient, IngredientCategory
from users.models import User


@pytest.fixture
def ingredient_category_data(factory: FixtureFactory) -> list[dict]:
    return factory.schema(
        lambda: {
            'name': factory.generic.text.word(),
        },
        iterations=10,
    ).create()


@pytest.fixture
def ingredient_category(ingredient_category_data: list[dict]) -> IngredientCategory:
    data = ingredient_category_data[0]
    return IngredientCategory.objects.create(**data)


@pytest.fixture
def second_ingredient_category(ingredient_category_data: list[dict]) -> IngredientCategory:
    data = ingredient_category_data[1]
    return IngredientCategory.objects.create(**data)


@pytest.fixture
def ingredient_categories(ingredient_category_data: list[dict]) -> list[IngredientCategory]:
    bulk_data = [IngredientCategory(**data) for data in ingredient_category_data[5::]]
    return IngredientCategory.objects.bulk_create(bulk_data)


@pytest.fixture
def ingredient_data(factory: FixtureFactory, ingredient_category: IngredientCategory) -> list[dict]:
    return factory.schema(
        lambda: {
            'name': factory.generic.text.word(),
            'owner': None,
            'base_unit': factory.generic.text.word(),
            'category': ingredient_category,
        },
        iterations=10,
    ).create()


@pytest.fixture
def ingredient_global(ingredient_data: list[dict]) -> Ingredient:
    data = ingredient_data[0]
    return Ingredient.objects.create(**data)


@pytest.fixture
def ingredient_user(ingredient_data: list[dict], telegram_user: User) -> Ingredient:
    data = ingredient_data[1]
    data['owner'] = telegram_user
    return Ingredient.objects.create(**data)


@pytest.fixture
def ingredients(ingredient_data: list[dict]) -> list[Ingredient]:
    bulk_data = [Ingredient(**data) for data in ingredient_data[5::]]
    return Ingredient.objects.bulk_create(bulk_data)
