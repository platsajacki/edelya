from pytest_mock import MockType

from typing import Any

from django.conf import settings

from apps.dishes.models import DishCategory, IngredientCategory
from apps.dishes.models.model_enums import Unit
from apps.dishes.services.dish_parser import RecipeAI
from apps.settings.models import Prompt


class TestRecipeSchemaBuilder:
    def test_builds_strict_schema_with_success_and_error_variants(
        self,
        recipe_root_schema: dict[str, Any],
    ) -> None:
        variants = recipe_root_schema['properties']['result']['anyOf']
        assert recipe_root_schema['additionalProperties'] is False
        assert recipe_root_schema['required'] == ['result']
        assert variants[0]['properties']['status']['enum'] == ['success']
        assert len(variants) == 7

    def test_uses_active_categories_and_units(
        self,
        recipe_root_schema: dict[str, Any],
        dish_category: DishCategory,
        ingredient_category: IngredientCategory,
    ) -> None:
        success_variant = recipe_root_schema['properties']['result']['anyOf'][0]
        dish_properties = success_variant['properties']['dish']['properties']
        ingredient_properties = success_variant['properties']['ingredients']['items']['properties']
        assert dish_properties['category_name']['enum'] == [dish_category.name]
        assert ingredient_properties['category_name']['enum'] == [ingredient_category.name]
        assert ingredient_properties['base_unit']['enum'] == list(Unit.values)

    def test_error_variants_keep_code_and_message_pairs(self, recipe_root_schema: dict[str, Any]) -> None:
        error_variants = recipe_root_schema['properties']['result']['anyOf'][1:]
        errors = {
            variant['properties']['error_code']['enum'][0]: variant['properties']['error_message']['enum'][0]
            for variant in error_variants
        }
        assert errors['not_recipe'] == (
            'Текст не похож на рецепт. Пришлите описание блюда с ингредиентами и приготовлением.'
        )
        assert errors['multiple_recipes'] == 'В тексте найдено несколько рецептов. Пришлите один рецепт за раз.'


class TestRecipeAI:
    def test_calls_openai_with_prompt_source_text_and_schema(
        self,
        mock_openai_create: MockType,
        mock_recipe_schema_builder: MockType,
        text_to_dish_prompt: Prompt,
    ) -> None:
        RecipeAI(source_text='Борщ')()
        call_kwargs = mock_openai_create.call_args.kwargs
        assert call_kwargs['model'] == settings.GPT_MODEL
        assert call_kwargs['messages'] == [
            {'role': 'developer', 'content': text_to_dish_prompt.text},
            {'role': 'user', 'content': 'Борщ'},
        ]
        assert call_kwargs['response_format']['type'] == 'json_schema'
        assert call_kwargs['response_format']['json_schema']['name'] == 'dish_recipe_parse'

    def test_returns_parsed_data_and_usage(
        self,
        mock_openai_create: MockType,
        mock_recipe_schema_builder: MockType,
        text_to_dish_prompt: Prompt,
    ) -> None:
        result = RecipeAI(source_text='Борщ')()
        assert result.data == {'result': {'status': 'error'}}
        assert result.usage == {'prompt_tokens': 10, 'completion_tokens': 5}
