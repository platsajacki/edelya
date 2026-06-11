from typing import Any

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

from apps.dishes.data_types import DishPayloadData


@deconstructible
class DishPayloadValidator:
    REQUIRED_DISH_KEYS = {'name', 'recipe', 'category', 'ingredients'}
    REQUIRED_ING_KEYS = {'ingredient', 'name', 'category', 'base_unit', 'amount', 'is_optional', 'new', 'suggested_ids'}

    def validate(self, payload: Any) -> DishPayloadData | None:
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise ValidationError('Payload must be a dictionary.')
        self._validate_structure(payload)
        self._validate_ingredients_list(payload)
        try:
            return DishPayloadData(**payload)  # type: ignore[typeddict-item]
        except TypeError as e:
            raise ValidationError(f'Invalid payload structure: {e}') from e

    def _validate_structure(self, payload: dict) -> None:
        if not self.REQUIRED_DISH_KEYS.issubset(payload.keys()):
            raise ValidationError('Payload must contain name, recipe, category and ingredients.')
        ingredients = payload['ingredients']
        if not isinstance(ingredients, list) or not ingredients:
            raise ValidationError('Ingredients must be a non-empty list.')

    def _validate_ingredients_list(self, payload: dict) -> None:
        for idx, ing in enumerate(payload['ingredients'], start=1):
            self._validate_ingredient(idx, ing)

    def _validate_ingredient(self, idx: int, ing: Any) -> None:
        if not isinstance(ing, dict):
            raise ValidationError(f'Ingredient #{idx} must be an object.')
        missing = self.REQUIRED_ING_KEYS - ing.keys()
        if missing:
            raise ValidationError(f'Ingredient #{idx} missing keys: {", ".join(sorted(missing))}.')
        if ing['ingredient'] is not None and not isinstance(ing['ingredient'], str):
            raise ValidationError(f'Ingredient #{idx} ingredient must be null or string.')
        if not all(isinstance(ing[k], str) for k in ('name', 'category', 'base_unit')):
            raise ValidationError(f'Ingredient #{idx} name/category/base_unit must be strings.')
        if not isinstance(ing['amount'], (int, float)):
            raise ValidationError(f'Ingredient #{idx} amount must be a number.')
        if not isinstance(ing['is_optional'], bool) or not isinstance(ing['new'], bool):
            raise ValidationError(f'Ingredient #{idx} is_optional and new must be booleans.')
        if not isinstance(ing['suggested_ids'], list) or not all(isinstance(i, str) for i in ing['suggested_ids']):
            raise ValidationError(f'Ingredient #{idx} suggested_ids must be a list of strings.')

    def __call__(self, payload: Any) -> DishPayloadData | None:
        return self.validate(payload)


dish_payload_validator = DishPayloadValidator()
