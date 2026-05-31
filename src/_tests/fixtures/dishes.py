import pytest
from pytest_mock import MockerFixture, MockType

from decimal import Decimal
from typing import Any, cast

from openai.types.shared_params.response_format_json_schema import JSONSchema

from _tests import FixtureFactory
from apps.dishes.models import Dish, DishAIDraft, DishCategory, DishIngredient
from apps.dishes.models.ingredients import Ingredient, IngredientCategory
from apps.dishes.models.model_enums import DishAIDraftStatus
from apps.dishes.services.recipe_schema_builder import RecipeSchemaBuilder
from apps.settings.model_enums import PromptName
from apps.settings.models import Prompt
from apps.subscriptions.constants import AI_RECIPE_LIMIT_PER_PERIOD
from apps.subscriptions.models import Subscription
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
            'name': f'{factory.generic.text.word()} {factory.generic.numeric.integer_number(start=1000, end=9999999)}',
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


@pytest.fixture
def dish_ai_draft(telegram_user: User) -> DishAIDraft:
    return DishAIDraft.objects.create(
        owner=telegram_user,
        source_text='Recipe source text',
    )


@pytest.fixture
def parsed_dish_ai_draft(telegram_user: User) -> DishAIDraft:
    return DishAIDraft.objects.create(
        owner=telegram_user,
        source_text='Parsed recipe source text',
        status=DishAIDraftStatus.PARSED,
        payload={'name': 'Parsed dish'},
    )


@pytest.fixture
def another_user_dish_ai_draft(another_telegram_user: User) -> DishAIDraft:
    return DishAIDraft.objects.create(
        owner=another_telegram_user,
        source_text='Another user recipe source text',
    )


@pytest.fixture
def dish_ai_draft_limit(telegram_user: User, active_subscription_with_period: Subscription) -> list[DishAIDraft]:
    drafts = [
        DishAIDraft(
            owner=telegram_user,
            source_text=f'Recipe source text {index}',
        )
        for index in range(AI_RECIPE_LIMIT_PER_PERIOD)
    ]
    return DishAIDraft.objects.bulk_create(drafts)


@pytest.fixture
def recipe_schema(dish_category: DishCategory, ingredient_category: IngredientCategory) -> JSONSchema:
    return RecipeSchemaBuilder()._build_recipe_json_schema()


@pytest.fixture
def recipe_root_schema(recipe_schema: JSONSchema) -> dict[str, Any]:
    return cast(dict[str, Any], recipe_schema['schema'])


@pytest.fixture
def text_to_dish_prompt() -> Prompt:
    return Prompt.objects.create(name=PromptName.TEXT_TO_DISH, text='Parse recipe')


@pytest.fixture
def recipe_ai_response(mocker: MockerFixture) -> MockType:
    response = mocker.MagicMock()
    response.choices[0].message.content = '{"result": {"status": "error"}}'
    response.usage.model_dump.return_value = {'prompt_tokens': 10, 'completion_tokens': 5}
    return response


@pytest.fixture
def mock_openai_create(mocker: MockerFixture, recipe_ai_response: MockType) -> MockType:
    return mocker.patch(
        'apps.dishes.services.dish_parser.openai_client.chat.completions.create',
        return_value=recipe_ai_response,
    )


@pytest.fixture
def mock_recipe_schema_builder(mocker: MockerFixture, recipe_schema: JSONSchema) -> MockType:
    return mocker.patch.object(RecipeSchemaBuilder, '__call__', return_value=recipe_schema)
