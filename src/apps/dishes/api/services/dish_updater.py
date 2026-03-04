from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.dishes.api.serializers.dishes import DishReadSerializer
from apps.dishes.models import Dish, DishIngredient, Ingredient
from core.base.services import BaseViewSetService


@dataclass
class DishUpdater(BaseViewSetService):
    dish: Dish | None = dc_field(default=None)
    queryset: QuerySet[Dish] = dc_field(default_factory=Dish.objects.none)

    def update_dish_fields(self, dish: Dish) -> None:
        upd_fields = []
        for field in self.validated_data:
            if hasattr(dish, field) and getattr(dish, field) != self.validated_data[field]:
                setattr(dish, field, self.validated_data[field])
                upd_fields.append(field)
        if upd_fields:
            dish.save(update_fields=upd_fields)

    def create_dish_ingredients(
        self, dish: Dish, dish_ingredients_data: list[dict], ingredients: dict[UUID, Ingredient]
    ) -> None:
        dish_ingredients = [
            DishIngredient(
                dish=dish,
                ingredient=ingredients[ingredient_data['ingredient']],
                is_optional=ingredient_data.get('is_optional', True),
                amount=ingredient_data['amount'],
            )
            for ingredient_data in dish_ingredients_data
        ]
        DishIngredient.objects.bulk_create(dish_ingredients)

    def create_or_update_dish_ingredients(
        self, dish: Dish, dish_ingredients_data: list[dict], ingredients: dict[UUID, Ingredient], is_creating: bool
    ) -> None:
        if is_creating:
            self.create_dish_ingredients(dish, dish_ingredients_data, ingredients)
            return
        self.upsert_dish_ingredients_bulk(dish, dish_ingredients_data, ingredients)

    def get_existing_dish_ingredients(self, dish: Dish) -> dict[UUID, DishIngredient]:
        existing = list(
            DishIngredient.objects.filter(dish=dish).only(
                'id',
                'ingredient_id',
                'amount',
                'is_optional',
            )
        )
        return {obj.ingredient_id: obj for obj in existing}

    def collect_create_and_update_dish_ingredients(
        self,
        dish: Dish,
        dish_ingredients_data: list[dict],
        ingredients: dict[UUID, Ingredient],
        existing_by_ingredient: dict[UUID, DishIngredient],
    ) -> tuple[list[DishIngredient], list[DishIngredient]]:
        to_create: list[DishIngredient] = []
        to_update: list[DishIngredient] = []
        for item in dish_ingredients_data:
            ingredient = ingredients[item['ingredient']]
            amount = item['amount']
            is_optional = item['is_optional']
            obj = existing_by_ingredient.pop(item['ingredient'], None)
            if obj is None:
                to_create.append(
                    DishIngredient(
                        dish=dish,
                        ingredient=ingredient,
                        amount=amount,
                        is_optional=is_optional,
                    )
                )
            else:
                if obj.amount != amount or obj.is_optional != is_optional:
                    obj.amount = amount
                    obj.is_optional = is_optional
                    to_update.append(obj)
        return to_create, to_update

    def upsert_dish_ingredients_bulk(
        self, dish: Dish, dish_ingredients_data: list[dict], ingredients: dict[UUID, Ingredient]
    ) -> None:
        existing_by_ingredient = self.get_existing_dish_ingredients(dish)
        to_create, to_update = self.collect_create_and_update_dish_ingredients(
            dish, dish_ingredients_data, ingredients, existing_by_ingredient
        )
        to_delete_ids = [obj.id for obj in existing_by_ingredient.values()]
        if to_delete_ids:
            DishIngredient.objects.filter(id__in=to_delete_ids).delete()
        if to_create:
            DishIngredient.objects.bulk_create(to_create)
        if to_update:
            DishIngredient.objects.bulk_update(to_update, fields=['amount', 'is_optional'])

    def get_ingredients_from_data(self, dish_ingredients_data: list[dict]) -> dict[UUID, Ingredient]:
        ingredient_ids = [item['ingredient'] for item in dish_ingredients_data]
        ingredients = list(
            Ingredient.objects.actived().for_user(self.validated_data['owner']).filter(id__in=ingredient_ids)
        )
        if len(ingredients) != len(ingredient_ids):
            existing_ids = {str(ing.id) for ing in ingredients}
            missing_ids = [str(ing_id) for ing_id in ingredient_ids if str(ing_id) not in existing_ids]
            raise NotFound(detail=f'Ingredients not found: {", ".join(missing_ids)}')
        return {ing.id: ing for ing in ingredients}

    def get_or_create_dish(self) -> tuple[Dish, bool]:
        if self.dish is not None:
            self.check_unique_constraints(create=False)
            self.update_dish_fields(self.dish)
            return self.dish, False
        self.check_unique_constraints(create=True)
        dish = Dish.objects.create(**self.validated_data)
        return dish, True

    def check_unique_constraints(self, create: bool) -> None:
        qs = self.queryset.filter(name__iexact=self.validated_data['name'], owner=self.validated_data['owner'])
        error = ValidationError(detail='Dish with this name already exists.')
        if create:
            if qs.exists():
                raise error
        elif self.dish is not None and qs.exclude(id=self.dish.id).exists():
            raise error

    @transaction.atomic
    def act(self) -> Response:
        dish_ingredients_data = self.validated_data.pop('dish_ingredients', [])
        if not dish_ingredients_data:
            return Response(
                {'detail': 'Dish must have at least one ingredient'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        dish, is_creating = self.get_or_create_dish()
        ingredients = self.get_ingredients_from_data(dish_ingredients_data)
        self.create_or_update_dish_ingredients(dish, dish_ingredients_data, ingredients, is_creating)
        dish = self.queryset.get(id=dish.id)
        serializer = DishReadSerializer(dish)
        return Response(serializer.data, status=status.HTTP_201_CREATED if is_creating else status.HTTP_200_OK)
