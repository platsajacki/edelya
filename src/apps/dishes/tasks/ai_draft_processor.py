from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import timedelta

from django.utils import timezone

from apps.dishes.data_types import DishPayloadData, IngredientPayloadData
from apps.dishes.models import DishAIDraft, DishAIDraftStatus, DishCategory, Ingredient
from apps.dishes.models.ingredients import IngredientCategory
from apps.dishes.services.dish_parser import (
    RecipeAI,
    RecipeAIErrorData,
    RecipeAIIngredientData,
    RecipeAIResult,
    RecipeAISuccessData,
)
from core import celery_app
from core.base.services import TaskService
from core.logging_handlers import tg_logger
from core.redis import redis_client
from core.utils import normalize_name


class AIDraftProcessingError(Exception): ...


@dataclass(frozen=True)
class PreparedIngredientData:
    source: RecipeAIIngredientData
    name: str
    category_name: str


@dataclass
class AIDraftProcessor(TaskService):
    draft_id: str
    _redis_lock_prefix: str = dc_field(default='ai_draft_processor_lock:')
    _redis_lock_expire: int = dc_field(default=180)
    _max_retries: int = dc_field(default=3)
    _another_category_name: str = dc_field(default='Другое')
    _exact_ingredient_similarity: float = dc_field(default=0.95)
    _similar_ingredient_similarity: float = dc_field(default=0.8)
    _similar_ingredients_limit: int = dc_field(default=3)

    def get_recipe_ai(self, draft: DishAIDraft) -> RecipeAIResult:
        attempt = 1
        while attempt <= self._max_retries:
            try:
                return RecipeAI(source_text=draft.source_text)()
            except Exception as e:
                tg_logger.error(
                    self.get_log_msg(f'Error creating RecipeAI for draft {self.draft_id} on attempt {attempt}: {e}')
                )
                attempt += 1
        raise AIDraftProcessingError(
            f'Failed to create RecipeAI for draft {self.draft_id} after {self._max_retries} attempts.'
        )

    def _handle_processing_error(self, draft: DishAIDraft, error_data: RecipeAIErrorData) -> None:
        draft.status = DishAIDraftStatus.FAILED
        draft.set_validation_error(
            error_code=error_data['error_code'], error_message=error_data['error_message'], save=False
        )
        draft.save(update_fields=['status', 'validation_errors'])

    def _get_category_id(self, category_name: str) -> str:
        category = DishCategory.objects.filter(name__iexact=category_name).first()
        if not category:
            category, _ = DishCategory.objects.get_or_create(name=self._another_category_name)
        return str(category.id)

    def _get_category_ids(self, category_names: list[str]) -> dict[str, str]:
        existing_categories = IngredientCategory.objects.get_by_names(category_names)
        if len(existing_categories) != len(set(category_names)):
            existing_category_names = {normalize_name(cat.name).lower() for cat in existing_categories}
            missing_categories = set(name.lower() for name in category_names) - existing_category_names
            tg_logger.warning(
                self.get_log_msg(
                    f'Missing ingredient categories: {missing_categories}. '
                    f'They will be created as "{self._another_category_name}".'
                )
            )
            raise AIDraftProcessingError(f'Missing ingredient categories: {missing_categories}.')
        return {normalize_name(cat.name).lower(): str(cat.id) for cat in existing_categories}

    def _prepare_ingredient_data(self, ingredient_data: list[RecipeAIIngredientData]) -> list[PreparedIngredientData]:
        prepared_data = []
        for ing in ingredient_data:
            name = normalize_name(ing['name']).lower()
            if not name:
                tg_logger.warning(
                    self.get_log_msg(f'Ingredient with empty name found in draft {self.draft_id}, skipping.')
                )
                continue
            category_name = self._get_ingredient_category_name(ing, name)
            prepared_data.append(PreparedIngredientData(source=ing, name=name, category_name=category_name))
        return prepared_data

    def _get_ingredient_category_name(self, ingredient: RecipeAIIngredientData, name: str) -> str:
        category_name = normalize_name(ingredient['category_name']).lower()
        if category_name:
            return category_name
        tg_logger.warning(
            self.get_log_msg(
                f'Ingredient "{name}" with empty category found in draft {self.draft_id}, '
                f'assigning to "{self._another_category_name}".'
            )
        )
        return self._another_category_name.lower()

    def _get_existing_ingredients_by_name(
        self, ingredient_names: list[str], draft: DishAIDraft
    ) -> dict[str, Ingredient]:
        existing_ingredients = Ingredient.objects.get_by_names_for_user(ingredient_names, user=draft.owner)
        return {normalize_name(ing.name).lower(): ing for ing in existing_ingredients}

    def _get_ingredient_payload(
        self,
        ingredient_data: PreparedIngredientData,
        draft: DishAIDraft,
        name_to_ingredient: dict[str, Ingredient],
        category_name_to_id: dict[str, str],
    ) -> IngredientPayloadData:
        ingredient = name_to_ingredient.get(ingredient_data.name)
        if ingredient is not None:
            return self._build_existing_ingredient_payload(ingredient, ingredient_data.source)
        similar_ingredients = self._get_similar_ingredients(ingredient_data.name, draft)
        exact_similar_ingredient = self._get_exact_similar_ingredient(similar_ingredients)
        if exact_similar_ingredient is not None:
            return self._build_existing_ingredient_payload(exact_similar_ingredient, ingredient_data.source)
        suggested_ids = [str(ingredient.id) for ingredient in similar_ingredients]
        return self._build_new_ingredient_payload(
            ingredient_data.source,
            category_name_to_id[ingredient_data.category_name],
            suggested_ids,
        )

    def _get_similar_ingredients(self, name: str, draft: DishAIDraft) -> list[Ingredient]:
        return list(
            Ingredient.objects.search_by_name_for_user(
                name,
                user=draft.owner,
                threshold=self._similar_ingredient_similarity,
                limit=self._similar_ingredients_limit,
            )
        )

    def _get_exact_similar_ingredient(self, ingredients: list[Ingredient]) -> Ingredient | None:
        if not ingredients:
            return None
        ingredient = ingredients[0]
        similarity = getattr(ingredient, 'similarity', 0)
        if similarity >= self._exact_ingredient_similarity:
            return ingredient
        return None

    def _build_existing_ingredient_payload(
        self, ingredient: Ingredient, ingredient_data: RecipeAIIngredientData
    ) -> IngredientPayloadData:
        return {
            'ingredient': str(ingredient.id),
            'name': ingredient.name,
            'category': str(ingredient.category_id),
            'base_unit': ingredient.base_unit,
            'amount': ingredient_data['amount'],
            'is_optional': ingredient_data['is_optional'],
            'new': False,
            'suggested_ids': [],
        }

    def _build_new_ingredient_payload(
        self, ingredient_data: RecipeAIIngredientData, category_id: str, suggested_ids: list[str]
    ) -> IngredientPayloadData:
        return {
            'ingredient': None,
            'name': normalize_name(ingredient_data['name']),
            'category': category_id,
            'base_unit': ingredient_data['base_unit'],
            'amount': ingredient_data['amount'],
            'is_optional': ingredient_data['is_optional'],
            'new': True,
            'suggested_ids': suggested_ids,
        }

    def _prepare_ingredients(
        self, ingredient_data: list[RecipeAIIngredientData], draft: DishAIDraft
    ) -> list[IngredientPayloadData]:
        prepared_data = self._prepare_ingredient_data(ingredient_data)
        category_name_to_id = self._get_category_ids([ing.category_name for ing in prepared_data])
        name_to_ingredient = self._get_existing_ingredients_by_name([ing.name for ing in prepared_data], draft)
        return [
            self._get_ingredient_payload(ing, draft, name_to_ingredient, category_name_to_id) for ing in prepared_data
        ]

    def _prepare_payload(self, success_data: RecipeAISuccessData, draft: DishAIDraft) -> DishPayloadData:
        category_name = success_data['dish']['category_name']
        category_id = self._get_category_id(category_name)
        ingredients = self._prepare_ingredients(success_data['ingredients'], draft)
        return {
            'name': normalize_name(success_data['dish']['name']),
            'recipe': success_data['dish']['recipe'],
            'category': category_id,
            'ingredients': ingredients,
        }

    def _handle_processing_success(self, draft: DishAIDraft, success_data: RecipeAISuccessData) -> None:
        draft.payload = self._prepare_payload(success_data, draft)
        draft.status = DishAIDraftStatus.PARSED
        draft.save(update_fields=['status', 'payload'])

    def _process_draft(self) -> None:
        try:
            draft = DishAIDraft.objects.get(id=self.draft_id)
            if draft.status != DishAIDraftStatus.PROCESSING:
                tg_logger.warning(
                    self.get_log_msg(f'Draft {self.draft_id} has status {draft.status}, skipping processing.')
                )
                return
            recipe_ai = self.get_recipe_ai(draft)
            if recipe_ai.data['result']['status'] == 'error':
                return self._handle_processing_error(draft, recipe_ai.data['result'])
            self._handle_processing_success(draft, recipe_ai.data['result'])
        except DishAIDraft.DoesNotExist:
            tg_logger.error(self.get_log_msg(f'Draft {self.draft_id} does not exist.'))
            return
        except AIDraftProcessingError as e:
            draft.status = DishAIDraftStatus.FAILED
            draft.set_validation_error(error_code='processing_error', error_message=str(e), save=False)
            draft.save(update_fields=['status', 'validation_errors'])

    def act(self) -> str:
        key = f'{self._redis_lock_prefix}{self.draft_id}'
        acquired_lock = redis_client.set(key, 'locked', nx=True, ex=self._redis_lock_expire)
        if not acquired_lock:
            return f'Draft {self.draft_id} is already being processed by another worker.'
        self._process_draft()
        return f'Draft {self.draft_id} processed.'


@celery_app.task
def process_ai_draft(draft_id: str) -> str:
    """
    Задача для обработки AI-черновиков блюд.
    """
    service = AIDraftProcessor(draft_id=draft_id)
    return service()


@celery_app.task
def process_ai_drafts_background(minutes: int = 3) -> None:
    """
    Периодическая задача для обработки AI-черновиков блюд,
    которые находятся в статусе PROCESSING дольше заданного количества минут.
    """
    drafts = DishAIDraft.objects.filter(
        created_at__lte=timezone.now() - timedelta(minutes=minutes),
        status=DishAIDraftStatus.PROCESSING,
    )
    for draft in drafts:
        process_ai_draft.delay(str(draft.id))
