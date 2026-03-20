from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

import yaml

from apps.dishes.models import (
    Dish,
    DishCategory,
    DishIngredient,
    Ingredient,
    IngredientCategory,
)

DATA_PATH = settings.BASE_DIR / 'data' / 'start_data.yaml'


class Command(BaseCommand):
    help = 'Load initial data for dishes and ingredients from a YAML file.'

    def get_yaml_data(self) -> dict[str, Any]:
        if not DATA_PATH.exists():
            raise CommandError(f'Start data file not found: {DATA_PATH}')
        with open(DATA_PATH, encoding='utf-8') as file:
            return yaml.safe_load(file)

    def load_data(
        self, model: type[DishCategory | IngredientCategory | Ingredient], data_list: list[dict[str, Any]]
    ) -> list[DishCategory | IngredientCategory | Ingredient]:
        objects = [model(**data) for data in data_list]
        return model.objects.bulk_create(objects, ignore_conflicts=True)  # type: ignore

    def prepare_ingredient_data(self, data: list[dict], ingredient_categories: list[IngredientCategory]) -> None:
        category_map = {cat.name: cat for cat in ingredient_categories}
        for item in data:
            category_name = item.pop('category')
            category = category_map.get(category_name)
            if not category:
                raise CommandError(f'Ingredient category not found: {category_name}')
            item['category'] = category

    def load_dishes(self, data: list[dict[str, Any]]) -> None:
        dish_category_map = {cat.name: cat for cat in DishCategory.objects.all()}
        ingredient_map = {ing.name: ing for ing in Ingredient.objects.all()}
        for item in data:
            category_name = item.pop('category')
            category = dish_category_map.get(category_name)
            if not category:
                raise CommandError(f'Dish category not found: {category_name}')
            ingredients_data = item.pop('ingredients')
            dish, _ = Dish.objects.get_or_create(
                name=item['name'],
                owner=None,
                defaults={'category': category, 'description': item.get('description', '')},
            )
            dish_ingredients = []
            for ing_data in ingredients_data:
                ingredient = ingredient_map.get(ing_data['name'])
                if not ingredient:
                    raise CommandError(f'Ingredient not found: {ing_data["name"]}')
                dish_ingredients.append(
                    DishIngredient(
                        dish=dish,
                        ingredient=ingredient,
                        amount=Decimal(str(ing_data['amount'])),
                        position=ing_data.get('position', 100),
                        is_optional=ing_data.get('is_optional', False),
                    )
                )
            DishIngredient.objects.bulk_create(dish_ingredients, ignore_conflicts=True)

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        data = self.get_yaml_data()
        if not data:
            raise CommandError('No data found in the YAML file.')
        self.stdout.write(self.style.SUCCESS('Starting to load initial data...'))
        self.load_data(DishCategory, data.get('dish_categories', []))
        ingredient_categories = self.load_data(IngredientCategory, data.get('ingredient_categories', []))
        self.prepare_ingredient_data(data.get('ingredients', []), ingredient_categories)  # type: ignore
        self.load_data(Ingredient, data.get('ingredients', []))
        self.load_dishes(data.get('dishes', []))
        self.stdout.write(self.style.SUCCESS('Initial data loaded successfully.'))
