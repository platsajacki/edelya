from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

import yaml

from apps.dishes.models import (
    DishCategory,
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
        self.stdout.write(self.style.SUCCESS('Initial data loaded successfully.'))
