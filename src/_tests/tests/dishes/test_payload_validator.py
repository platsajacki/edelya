import pytest

from copy import deepcopy

from django.core.exceptions import ValidationError

from apps.dishes.data_types import DishPayloadData
from apps.dishes.models.validators import DishPayloadValidator


class TestDishPayloadValidator:
    def test_valid_payload_returns_payload_data(self, valid_dish_payload: DishPayloadData) -> None:
        result = DishPayloadValidator()(valid_dish_payload)
        assert result == valid_dish_payload

    def test_none_payload_returns_none(self) -> None:
        assert DishPayloadValidator()(None) is None

    def test_non_dict_payload_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError, match='Payload must be a dictionary.'):
            DishPayloadValidator()(['not-a-dict'])

    def test_missing_dish_keys_raises_validation_error(self, valid_dish_payload: DishPayloadData) -> None:
        payload = deepcopy(valid_dish_payload)
        del payload['name']  # type: ignore[misc]
        with pytest.raises(ValidationError, match='Payload must contain name, recipe, category and ingredients.'):
            DishPayloadValidator()(payload)

    def test_empty_ingredients_raises_validation_error(self, valid_dish_payload: DishPayloadData) -> None:
        payload = deepcopy(valid_dish_payload)
        payload['ingredients'] = []
        with pytest.raises(ValidationError, match='Ingredients must be a non-empty list.'):
            DishPayloadValidator()(payload)

    def test_non_list_ingredients_raises_validation_error(self, valid_dish_payload: DishPayloadData) -> None:
        payload = deepcopy(valid_dish_payload)
        payload['ingredients'] = 'not-a-list'  # type: ignore[typeddict-item]
        with pytest.raises(ValidationError, match='Ingredients must be a non-empty list.'):
            DishPayloadValidator()(payload)

    def test_non_dict_ingredient_raises_validation_error(self, valid_dish_payload: DishPayloadData) -> None:
        payload = deepcopy(valid_dish_payload)
        payload['ingredients'] = ['not-a-dict']  # type: ignore[list-item]
        with pytest.raises(ValidationError, match='Ingredient #1 must be an object.'):
            DishPayloadValidator()(payload)

    def test_missing_ingredient_keys_raises_validation_error(self, valid_dish_payload: DishPayloadData) -> None:
        payload = deepcopy(valid_dish_payload)
        del payload['ingredients'][0]['base_unit']  # type: ignore[misc]
        with pytest.raises(ValidationError, match='Ingredient #1 missing keys: base_unit.'):
            DishPayloadValidator()(payload)

    def test_invalid_ingredient_string_fields_raise_validation_error(
        self,
        valid_dish_payload: DishPayloadData,
    ) -> None:
        payload = deepcopy(valid_dish_payload)
        payload['ingredients'][0]['name'] = 123  # type: ignore[typeddict-item]
        with pytest.raises(ValidationError, match='Ingredient #1 name/category/base_unit must be strings.'):
            DishPayloadValidator()(payload)

    def test_invalid_amount_raises_validation_error(self, valid_dish_payload: DishPayloadData) -> None:
        payload = deepcopy(valid_dish_payload)
        payload['ingredients'][0]['amount'] = '300'  # type: ignore[typeddict-item]
        with pytest.raises(ValidationError, match='Ingredient #1 amount must be a number.'):
            DishPayloadValidator()(payload)

    def test_invalid_boolean_fields_raise_validation_error(self, valid_dish_payload: DishPayloadData) -> None:
        payload = deepcopy(valid_dish_payload)
        payload['ingredients'][0]['new'] = 'true'  # type: ignore[typeddict-item]
        with pytest.raises(ValidationError, match='Ingredient #1 is_optional and new must be booleans.'):
            DishPayloadValidator()(payload)

    def test_invalid_suggested_ids_raise_validation_error(self, valid_dish_payload: DishPayloadData) -> None:
        payload = deepcopy(valid_dish_payload)
        payload['ingredients'][0]['suggested_ids'] = [123]  # type: ignore[list-item]
        with pytest.raises(ValidationError, match='Ingredient #1 suggested_ids must be a list of strings.'):
            DishPayloadValidator()(payload)

    def test_extra_payload_and_ingredient_keys_are_allowed(self, valid_dish_payload: DishPayloadData) -> None:
        payload = deepcopy(valid_dish_payload)
        payload['extra'] = 'allowed'  # type: ignore[typeddict-unknown-key]
        payload['ingredients'][0]['extra'] = 'allowed'  # type: ignore[typeddict-unknown-key]
        result = DishPayloadValidator()(payload)
        assert result == payload
