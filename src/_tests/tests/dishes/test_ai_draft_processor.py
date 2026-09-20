import pytest
from pytest_mock import MockFixture, MockType

import json
from collections.abc import Callable
from copy import deepcopy
from uuid import uuid4

from _tests.fixtures.open_ai import OpenAIErrorFactory
from apps.dishes.models import DishAIDraft, DishCategory, Ingredient, IngredientCategory, Unit
from apps.dishes.models.model_enums import DishAIDraftStatus
from apps.dishes.services.dish_parser import RecipeAIResult, RecipeAISuccessData
from apps.dishes.tasks.ai_draft_processor import AIDraftProcessingError, AIDraftProcessor, PreparedIngredientData


class TestGetRecipeAI:
    def test_returns_recipe_ai_result(
        self,
        dish_ai_draft: DishAIDraft,
        recipe_ai_success_result: RecipeAIResult,
        mock_ai_draft_processor_recipe_ai: MockType,
    ) -> None:
        mock_ai_draft_processor_recipe_ai.return_value.return_value = recipe_ai_success_result
        result = AIDraftProcessor(draft_id=str(dish_ai_draft.id)).get_recipe_ai(dish_ai_draft)
        assert result == recipe_ai_success_result

    def test_retries_rate_limit_with_retry_after_delay(
        self,
        dish_ai_draft: DishAIDraft,
        recipe_ai_success_result: RecipeAIResult,
        mock_ai_draft_processor_recipe_ai: MockType,
        mock_ai_draft_processor_sleep: MockType,
        openai_error_factory: OpenAIErrorFactory,
    ) -> None:
        recipe_ai = mock_ai_draft_processor_recipe_ai.return_value
        error = openai_error_factory.rate_limit(headers={'retry-after-ms': '1500'})
        recipe_ai.side_effect = [error, recipe_ai_success_result]
        processor = AIDraftProcessor(draft_id=str(dish_ai_draft.id))
        result = processor.get_recipe_ai(dish_ai_draft)
        assert result == recipe_ai_success_result
        assert recipe_ai.call_count == 2
        delay = mock_ai_draft_processor_sleep.call_args.args[0]
        assert 1.5 <= delay <= 1.5 + processor._retry_policy.jitter_sec

    @pytest.mark.parametrize('error_name', ['server_error', 'connection_error'])
    def test_retries_transient_openai_errors(
        self,
        error_name: str,
        dish_ai_draft: DishAIDraft,
        recipe_ai_success_result: RecipeAIResult,
        mock_ai_draft_processor_recipe_ai: MockType,
        mock_ai_draft_processor_sleep: MockType,
        openai_error_factory: OpenAIErrorFactory,
    ) -> None:
        recipe_ai = mock_ai_draft_processor_recipe_ai.return_value
        recipe_ai.side_effect = [getattr(openai_error_factory, error_name)(), recipe_ai_success_result]
        result = AIDraftProcessor(draft_id=str(dish_ai_draft.id)).get_recipe_ai(dish_ai_draft)
        assert result == recipe_ai_success_result
        mock_ai_draft_processor_sleep.assert_called_once()

    def test_raises_processing_error_after_attempts_exhaustion(
        self,
        dish_ai_draft: DishAIDraft,
        mock_ai_draft_processor_recipe_ai: MockType,
        mock_ai_draft_processor_sleep: MockType,
        openai_error_factory: OpenAIErrorFactory,
    ) -> None:
        recipe_ai = mock_ai_draft_processor_recipe_ai.return_value
        recipe_ai.side_effect = openai_error_factory.rate_limit()
        processor = AIDraftProcessor(draft_id=str(dish_ai_draft.id))
        with pytest.raises(AIDraftProcessingError):
            processor.get_recipe_ai(dish_ai_draft)
        assert recipe_ai.call_count == processor._max_attempts
        assert mock_ai_draft_processor_sleep.call_count == processor._max_attempts - 1

    @pytest.mark.parametrize(
        'error_builder',
        [
            lambda factory: factory.rate_limit(code='insufficient_quota'),
            lambda factory: factory.rate_limit(message='Please try again in 1m30s.'),
            lambda factory: factory.bad_request(),
            lambda factory: ValueError('No active dish categories'),
            lambda factory: json.JSONDecodeError('Expecting value', '', 0),
        ],
        ids=['insufficient_quota', 'long_retry_after', 'bad_request', 'value_error', 'json_decode_error'],
    )
    def test_raises_processing_error_without_retry(
        self,
        error_builder: Callable[[OpenAIErrorFactory], Exception],
        dish_ai_draft: DishAIDraft,
        mock_ai_draft_processor_recipe_ai: MockType,
        mock_ai_draft_processor_sleep: MockType,
        openai_error_factory: OpenAIErrorFactory,
    ) -> None:
        recipe_ai = mock_ai_draft_processor_recipe_ai.return_value
        recipe_ai.side_effect = error_builder(openai_error_factory)
        with pytest.raises(AIDraftProcessingError):
            AIDraftProcessor(draft_id=str(dish_ai_draft.id)).get_recipe_ai(dish_ai_draft)
        assert recipe_ai.call_count == 1
        mock_ai_draft_processor_sleep.assert_not_called()


class TestPreparePayload:
    def test_builds_payload_with_normalized_dish_and_new_ingredient(
        self,
        dish_ai_draft: DishAIDraft,
        dish_category: DishCategory,
        ingredient_category: IngredientCategory,
        recipe_ai_success_data: RecipeAISuccessData,
        mocker: MockFixture,
    ) -> None:
        processor = AIDraftProcessor(draft_id=str(dish_ai_draft.id))
        mocker.patch.object(processor, '_get_similar_ingredients', return_value=[])
        payload = processor._prepare_payload(recipe_ai_success_data, dish_ai_draft)
        assert payload == {
            'name': 'Борщ домашний',
            'recipe': recipe_ai_success_data['dish']['recipe'],
            'category': str(dish_category.id),
            'ingredients': [
                {
                    'ingredient': None,
                    'name': 'Свекла',
                    'category': str(ingredient_category.id),
                    'base_unit': Unit.GRAM,
                    'owner': None,
                    'amount': 300.0,
                    'is_optional': False,
                    'new': True,
                    'suggested_ids': [],
                },
            ],
        }

    def test_normalizes_literal_recipe_newlines(
        self,
        dish_ai_draft: DishAIDraft,
        recipe_ai_success_data: RecipeAISuccessData,
        mocker: MockFixture,
    ) -> None:
        data = deepcopy(recipe_ai_success_data)
        data['dish']['recipe'] = '1. Нарезать овощи\\n2. Сварить суп\\r\\n3. Подать'
        processor = AIDraftProcessor(draft_id=str(dish_ai_draft.id))
        mocker.patch.object(processor, '_prepare_ingredients', return_value=[])
        payload = processor._prepare_payload(data, dish_ai_draft)
        assert payload['recipe'] == '1. Нарезать овощи\n2. Сварить суп\n3. Подать'

    def test_unknown_dish_category_raises_processing_error(
        self,
        dish_ai_draft: DishAIDraft,
        ingredient_category: IngredientCategory,
        recipe_ai_success_data: RecipeAISuccessData,
        mocker: MockFixture,
    ) -> None:
        data = deepcopy(recipe_ai_success_data)
        data['dish']['category_name'] = 'Несуществующая категория'
        processor = AIDraftProcessor(draft_id=str(dish_ai_draft.id))
        mocker.patch.object(processor, '_get_similar_ingredients', return_value=[])
        with pytest.raises(AIDraftProcessingError, match='Dish category not found'):
            processor._prepare_payload(data, dish_ai_draft)
        assert not DishCategory.objects.filter(name='Другое').exists()

    def test_empty_ingredient_category_raises_processing_error(
        self,
        dish_ai_draft: DishAIDraft,
        recipe_ai_success_data: RecipeAISuccessData,
        mocker: MockFixture,
    ) -> None:
        data = deepcopy(recipe_ai_success_data)
        data['ingredients'][0]['category_name'] = '   '
        processor = AIDraftProcessor(draft_id=str(dish_ai_draft.id))
        mocker.patch.object(processor, '_get_similar_ingredients', return_value=[])
        with pytest.raises(AIDraftProcessingError, match='has no category'):
            processor._prepare_payload(data, dish_ai_draft)

    def test_existing_ingredient_by_name_is_not_new(
        self,
        dish_ai_draft: DishAIDraft,
        dish_category: DishCategory,
        ingredient_user: Ingredient,
        recipe_ai_success_data: RecipeAISuccessData,
        mocker: MockFixture,
    ) -> None:
        data = deepcopy(recipe_ai_success_data)
        data['ingredients'][0]['name'] = f'  {ingredient_user.name}  '
        data['ingredients'][0]['category_name'] = ingredient_user.category.name
        processor = AIDraftProcessor(draft_id=str(dish_ai_draft.id))
        mocker.patch.object(processor, '_get_similar_ingredients', return_value=[])
        payload = processor._prepare_payload(data, dish_ai_draft)
        assert payload['category'] == str(dish_category.id)
        assert payload['ingredients'][0] == {
            'ingredient': str(ingredient_user.id),
            'name': ingredient_user.name,
            'category': str(ingredient_user.category_id),
            'base_unit': ingredient_user.base_unit,
            'owner': str(ingredient_user.owner_id),
            'amount': 300.0,
            'is_optional': False,
            'new': False,
            'suggested_ids': [],
        }

    def test_exact_similar_ingredient_is_not_new(
        self,
        dish_ai_draft: DishAIDraft,
        ingredient_global: Ingredient,
        recipe_ai_success_data: RecipeAISuccessData,
        mocker: MockFixture,
    ) -> None:
        ingredient_global.similarity = 0.95  # type: ignore[attr-defined]
        processor = AIDraftProcessor(draft_id=str(dish_ai_draft.id))
        ingredient_data = PreparedIngredientData(
            source=recipe_ai_success_data['ingredients'][0],
            name='свекла',
            category_name=ingredient_global.category.name.lower(),
        )
        mocker.patch.object(processor, '_get_similar_ingredients', return_value=[ingredient_global])
        payload = processor._get_ingredient_payload(
            ingredient_data,
            dish_ai_draft,
            name_to_ingredient={},
            category_name_to_id={ingredient_global.category.name.lower(): str(ingredient_global.category_id)},
        )
        assert payload == {
            'ingredient': str(ingredient_global.id),
            'name': ingredient_global.name,
            'category': str(ingredient_global.category_id),
            'base_unit': ingredient_global.base_unit,
            'owner': None,
            'amount': 300.0,
            'is_optional': False,
            'new': False,
            'suggested_ids': [],
        }

    def test_similar_ingredients_become_suggestions_for_new_ingredient(
        self,
        dish_ai_draft: DishAIDraft,
        ingredient_global: Ingredient,
        ingredient_user: Ingredient,
        recipe_ai_success_data: RecipeAISuccessData,
        mocker: MockFixture,
    ) -> None:
        ingredient_global.similarity = 0.9  # type: ignore[attr-defined]
        ingredient_user.similarity = 0.85  # type: ignore[attr-defined]
        processor = AIDraftProcessor(draft_id=str(dish_ai_draft.id))
        ingredient_data = PreparedIngredientData(
            source=recipe_ai_success_data['ingredients'][0],
            name='свекла',
            category_name=ingredient_global.category.name.lower(),
        )
        mocker.patch.object(processor, '_get_similar_ingredients', return_value=[ingredient_global, ingredient_user])
        payload = processor._get_ingredient_payload(
            ingredient_data,
            dish_ai_draft,
            name_to_ingredient={},
            category_name_to_id={ingredient_global.category.name.lower(): str(ingredient_global.category_id)},
        )
        assert payload['new'] is True
        assert payload['suggested_ids'] == [str(ingredient_global.id), str(ingredient_user.id)]

    def test_unknown_ingredient_category_raises_processing_error(
        self,
        dish_ai_draft: DishAIDraft,
        recipe_ai_success_data: RecipeAISuccessData,
    ) -> None:
        data = deepcopy(recipe_ai_success_data)
        data['ingredients'][0]['category_name'] = 'Несуществующая категория'
        processor = AIDraftProcessor(draft_id=str(dish_ai_draft.id))
        with pytest.raises(AIDraftProcessingError):
            processor._prepare_payload(data, dish_ai_draft)


class TestProcessDraft:
    def test_ai_success_sets_parsed_status_and_payload(
        self,
        dish_ai_draft: DishAIDraft,
        dish_category: DishCategory,
        ingredient_category: IngredientCategory,
        recipe_ai_success_result: RecipeAIResult,
        mocker: MockFixture,
    ) -> None:
        processor = AIDraftProcessor(draft_id=str(dish_ai_draft.id))
        mocker.patch.object(processor, 'get_recipe_ai', return_value=recipe_ai_success_result)
        mocker.patch.object(processor, '_get_similar_ingredients', return_value=[])
        processor._process_draft()
        dish_ai_draft.refresh_from_db()
        assert dish_ai_draft.status == DishAIDraftStatus.PARSED
        assert dish_ai_draft.payload == {
            'name': 'Борщ домашний',
            'recipe': recipe_ai_success_result.data['result']['dish']['recipe'],  # type: ignore[typeddict-item]
            'category': str(dish_category.id),
            'ingredients': [
                {
                    'ingredient': None,
                    'name': 'Свекла',
                    'category': str(ingredient_category.id),
                    'base_unit': Unit.GRAM,
                    'owner': None,
                    'amount': 300.0,
                    'is_optional': False,
                    'new': True,
                    'suggested_ids': [],
                },
            ],
        }
        assert dish_ai_draft.ai_raw_response == recipe_ai_success_result.data
        assert dish_ai_draft.usage == recipe_ai_success_result.usage

    def test_ai_error_sets_failed_status_and_validation_error(
        self,
        dish_ai_draft: DishAIDraft,
        recipe_ai_error_result: RecipeAIResult,
        mocker: MockFixture,
    ) -> None:
        processor = AIDraftProcessor(draft_id=str(dish_ai_draft.id))
        mocker.patch.object(processor, 'get_recipe_ai', return_value=recipe_ai_error_result)
        processor._process_draft()
        dish_ai_draft.refresh_from_db()
        assert dish_ai_draft.status == DishAIDraftStatus.FAILED
        assert dish_ai_draft.validation_errors == [
            {
                'error_code': 'not_recipe',
                'error_message': 'Текст не похож на рецепт. Пришлите описание блюда с ингредиентами и приготовлением.',
            },
        ]
        assert dish_ai_draft.ai_raw_response == recipe_ai_error_result.data
        assert dish_ai_draft.usage == recipe_ai_error_result.usage

    def test_skips_draft_with_non_processing_status(
        self,
        parsed_dish_ai_draft: DishAIDraft,
        mocker: MockFixture,
    ) -> None:
        processor = AIDraftProcessor(draft_id=str(parsed_dish_ai_draft.id))
        mock_get_recipe_ai = mocker.patch.object(processor, 'get_recipe_ai')
        processor._process_draft()
        parsed_dish_ai_draft.refresh_from_db()
        assert parsed_dish_ai_draft.status == DishAIDraftStatus.PARSED
        mock_get_recipe_ai.assert_not_called()

    def test_missing_draft_does_not_raise(self) -> None:
        AIDraftProcessor(draft_id=str(uuid4()))._process_draft()

    def test_processing_error_sets_failed_status_and_validation_error(
        self,
        dish_ai_draft: DishAIDraft,
        mocker: MockFixture,
    ) -> None:
        processor = AIDraftProcessor(draft_id=str(dish_ai_draft.id))
        mocker.patch.object(processor, 'get_recipe_ai', side_effect=AIDraftProcessingError('Invalid categories'))
        processor._process_draft()
        dish_ai_draft.refresh_from_db()
        assert dish_ai_draft.status == DishAIDraftStatus.FAILED
        assert dish_ai_draft.validation_errors == [
            {
                'error_code': 'processing_error',
                'error_message': 'Invalid categories',
            },
        ]
        assert dish_ai_draft.ai_raw_response is None
        assert dish_ai_draft.usage is None


class TestAct:
    def test_returns_already_processing_message_when_lock_is_not_acquired(
        self,
        dish_ai_draft: DishAIDraft,
        mock_ai_draft_processor_redis_set: MockType,
        mocker: MockFixture,
    ) -> None:
        mock_ai_draft_processor_redis_set.return_value = None
        processor = AIDraftProcessor(draft_id=str(dish_ai_draft.id))
        mock_process = mocker.patch.object(processor, '_process_draft')
        result = processor()
        assert result == f'Draft {dish_ai_draft.id} is already being processed by another worker.'
        mock_process.assert_not_called()

    def test_processes_draft_when_lock_is_acquired(
        self,
        dish_ai_draft: DishAIDraft,
        mock_ai_draft_processor_redis_set: MockType,
        mocker: MockFixture,
    ) -> None:
        mock_ai_draft_processor_redis_set.return_value = True
        processor = AIDraftProcessor(draft_id=str(dish_ai_draft.id))
        mock_process = mocker.patch.object(processor, '_process_draft')
        result = processor()
        assert result == f'Draft {dish_ai_draft.id} processed.'
        mock_process.assert_called_once_with()
