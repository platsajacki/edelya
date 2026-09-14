from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.cache import caches

from openai.types.shared_params.response_format_json_schema import JSONSchema

from apps.dishes.models.dishes import DishCategory
from apps.dishes.models.ingredients import IngredientCategory
from apps.dishes.models.model_enums import Unit
from core.base.services import BaseService

_RECIPE_PARSE_ERROR_MESSAGES = {
    'not_recipe': 'Текст не похож на рецепт. Пришлите описание блюда с ингредиентами и приготовлением.',
    'multiple_recipes': 'В тексте найдено несколько рецептов. Пришлите один рецепт за раз.',
    'prompt_injection': (
        'Обнаружены подозрительные данные, похожие на попытку обойти систему. '
        'Пожалуйста, измените формулировку и попробуйте снова.'
    ),
    'not_processable': 'Рецепт не может быть обработан. Пожалуйста, проверьте формат и содержание текста.',
}


@dataclass
class RecipeSchemaBuilder(BaseService[JSONSchema]):
    cache_key: str = 'ai:recipe_schema'
    cache_timeout: int = 60 * 60 * 24  # 24 часа

    def _object_schema(self, properties: dict[str, Any]) -> dict[str, Any]:
        return {
            'type': 'object',
            'additionalProperties': False,
            'properties': properties,
            'required': list(properties),
        }

    def _string_schema(self, description: str, enum: list[str] | None = None) -> dict[str, Any]:
        schema: dict[str, Any] = {'type': 'string', 'description': description}
        if enum is not None:
            schema['enum'] = enum
        return schema

    def _build_error_variant(self, error_code: str, error_message: str) -> dict[str, Any]:
        return self._object_schema(
            {
                'status': self._string_schema('Статус ошибки разбора.', ['error']),
                'error_code': self._string_schema('Код ошибки из заранее разрешённого списка.', [error_code]),
                'error_message': self._string_schema(
                    'Готовый текст ошибки. Нельзя изменять формулировку.',
                    [error_message],
                ),
            }
        )

    def _get_error_variants(self) -> list[dict[str, Any]]:
        return [self._build_error_variant(code, message) for code, message in _RECIPE_PARSE_ERROR_MESSAGES.items()]

    def _build_dish_schema(self) -> dict[str, Any]:
        return self._object_schema(
            {
                'name': self._string_schema('Название блюда с заглавной буквы, в именительном падеже.'),
                'recipe': self._string_schema('Пронумерованные шаги приготовления. Каждый шаг с новой строки.'),
                'category_name': self._string_schema(
                    'Категория блюда. Выбрать наиболее подходящее значение из enum.',
                    self.get_dish_categories(),
                ),
            }
        )

    def _build_ingredient_schema(self) -> dict[str, Any]:
        return self._object_schema(
            {
                'name': self._string_schema(
                    'Название ингредиента в единственном числе, именительном падеже, с заглавной буквы.'
                ),
                'category_name': self._string_schema(
                    'Категория ингредиента. Выбрать наиболее подходящее значение из enum.',
                    self.get_ingredient_categories(),
                ),
                'base_unit': self._string_schema(
                    'Базовая единица измерения ингредиента. Выбрать подходящее значение из enum.',
                    self.get_units(),
                ),
                'amount': {
                    'type': 'number',
                    'exclusiveMinimum': 0,
                    'description': 'Количество ингредиента в base_unit.',
                },
                'position': {
                    'type': 'integer',
                    'minimum': 1,
                    'description': 'Порядковый номер первого появления ингредиента в рецепте.',
                },
                'is_optional': {
                    'type': 'boolean',
                    'description': 'true только если явно указано, что ингредиент необязателен.',
                },
            }
        )

    def _build_success_variant(self) -> dict[str, Any]:
        return self._object_schema(
            {
                'status': self._string_schema('Рецепт успешно разобран.', ['success']),
                'dish': self._build_dish_schema(),
                'ingredients': {
                    'type': 'array',
                    'minItems': 1,
                    'items': self._build_ingredient_schema(),
                },
            }
        )

    def _build_recipe_json_schema(self) -> JSONSchema:
        return {
            'name': 'dish_recipe_parse',
            'strict': True,
            'schema': self._object_schema(
                {
                    'result': {
                        'anyOf': [
                            self._build_success_variant(),
                            *self._get_error_variants(),
                        ],
                    }
                }
            ),
        }

    def get_dish_categories(self) -> list[str]:
        categories = list(DishCategory.objects.actived().values_list('name', flat=True))
        if not categories:
            raise ValueError('No active dish categories')
        return categories

    def get_ingredient_categories(self) -> list[str]:
        categories = list(IngredientCategory.objects.actived().values_list('name', flat=True))
        if not categories:
            raise ValueError('No active ingredient categories')
        return categories

    def get_units(self) -> list[str]:
        units = [unit.value for unit in Unit]
        if not units:
            raise ValueError('No units')
        return units

    def act(self) -> JSONSchema:
        cache = caches[settings.AI_CACHE_ALIAS]
        if cached_schema := cache.get(self.cache_key):
            return cached_schema
        schema = self._build_recipe_json_schema()
        cache.set(self.cache_key, schema, self.cache_timeout)
        return schema
