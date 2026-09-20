from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any

from django.db import transaction
from django.db.models import QuerySet
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.dishes.api.serializers.dishes import DishWriteSerializer
from apps.dishes.api.services.dish_updater import DishUpdater
from apps.dishes.data_types import DishPayloadData, IngredientPayloadData
from apps.dishes.models import Dish, DishAIDraft, DishAIDraftStatus, Ingredient, IngredientCategory, Unit
from core.base.services import BaseViewSetService
from core.utils import normalize_name


@dataclass
class AIDraftService:
    draft: DishAIDraft = dc_field(kw_only=True)


@dataclass
class AIDraftDishCreator(AIDraftService, BaseViewSetService):
    queryset: QuerySet[Dish] = dc_field(default_factory=Dish.objects.none)

    def validate_draft_status(self) -> None:
        if self.draft.status != DishAIDraftStatus.PARSED:
            raise ValidationError('AI draft must be parsed before dish creation.')

    def get_validators(self) -> list:
        return super().get_validators() + [self.validate_draft_status]

    def _validate_new_ingredient(self, item: IngredientPayloadData) -> None:
        if item['ingredient'] is not None:
            raise ValidationError('New ingredient must not contain ingredient id.')
        if item['base_unit'] not in Unit.values:
            raise ValidationError(f'Invalid ingredient unit: {item["base_unit"]}')
        if not IngredientCategory.objects.actived().filter(id=item['category']).exists():
            raise ValidationError(f'Ingredient category not found: {item["category"]}')

    def _validate_existing_ingredient(self, item: IngredientPayloadData) -> None:
        if item['ingredient'] is None:
            raise ValidationError('Existing ingredient id is required.')

    def _validate_existing_ingredients(self, items: list[IngredientPayloadData]) -> None:
        for item in items:
            self._validate_existing_ingredient(item)

    def build_new_ingredient(self, item: IngredientPayloadData, name: str) -> Ingredient:
        self._validate_new_ingredient(item)
        return Ingredient(
            owner=self.draft.owner,
            name=name,
            category_id=item['category'],
            base_unit=item['base_unit'],
        )

    def get_owned_ingredients_by_name(self, names: list[str]) -> dict[str, Ingredient]:
        ingredients = Ingredient.objects.get_by_names_for_user(names, self.draft.owner)
        return {normalize_name(ingredient.name).lower(): ingredient for ingredient in ingredients}

    def get_new_ingredients(self, items: list[IngredientPayloadData]) -> dict[str, Ingredient]:
        names = [normalize_name(item['name']) for item in items]
        ingredient_by_name = self.get_owned_ingredients_by_name(names)
        to_create: dict[str, Ingredient] = {}
        for item, name in zip(items, names, strict=True):
            key = name.lower()
            if key not in ingredient_by_name and key not in to_create:
                to_create[key] = self.build_new_ingredient(item, name)
        Ingredient.objects.bulk_create(list(to_create.values()))
        return {**ingredient_by_name, **to_create}

    def get_existing_ingredients(self, items: list[IngredientPayloadData]) -> dict[str, Ingredient]:
        self._validate_existing_ingredients(items)
        ingredient_ids = {item['ingredient'] for item in items if item['ingredient'] is not None}
        ingredients = Ingredient.objects.for_user(self.draft.owner).filter(id__in=ingredient_ids)
        ingredient_by_id = {str(ingredient.id): ingredient for ingredient in ingredients}
        missing_ids = sorted(ingredient_ids - ingredient_by_id.keys())
        if missing_ids:
            raise NotFound(detail=f'Ingredients not found: {", ".join(missing_ids)}')
        return ingredient_by_id

    def resolve_ingredient(
        self, item: IngredientPayloadData, new_by_name: dict[str, Ingredient], existing_by_id: dict[str, Ingredient]
    ) -> Ingredient:
        if item['new']:
            return new_by_name[normalize_name(item['name']).lower()]
        ingredient_id = item['ingredient']
        if ingredient_id is None:
            raise ValidationError('Existing ingredient id is required.')
        return existing_by_id[ingredient_id]

    def get_ingredients(self, items: list[IngredientPayloadData]) -> list[Ingredient]:
        new_by_name = self.get_new_ingredients([item for item in items if item['new']])
        existing_by_id = self.get_existing_ingredients([item for item in items if not item['new']])
        return [self.resolve_ingredient(item, new_by_name, existing_by_id) for item in items]

    def get_dish_name(self, name: str) -> str:
        if self.queryset.filter(name__iexact=name, owner=self.draft.owner).exists():
            return f'{name} (AI)'
        return name

    def build_dish_payload(self, payload: DishPayloadData) -> dict[str, Any]:
        ingredients = self.get_ingredients(payload['ingredients'])
        dish_ingredients = []
        for item, ingredient in zip(payload['ingredients'], ingredients, strict=True):
            dish_ingredients.append(
                {
                    'ingredient': str(ingredient.id),
                    'amount': item['amount'],
                    'is_optional': item['is_optional'],
                }
            )
        return {
            'category': payload['category'],
            'name': self.get_dish_name(payload['name']),
            'recipe': payload['recipe'],
            'dish_ingredients': dish_ingredients,
        }

    def create_dish(self, payload: DishPayloadData) -> Response:
        serializer = DishWriteSerializer(
            data=self.build_dish_payload(payload),
            context=self.serializer.context,
        )
        return DishUpdater(
            serializer=serializer,
            dish=None,
            queryset=self.queryset,
        )()

    @transaction.atomic
    def act(self) -> Response:
        response = self.create_dish(self.validated_data['payload'])
        self.draft.payload = self.validated_data['payload']
        self.draft.created_dish_id = response.data['id']
        self.draft.status = DishAIDraftStatus.DISH_CREATED
        self.draft.save(update_fields=['payload', 'created_dish', 'status'])
        return response
