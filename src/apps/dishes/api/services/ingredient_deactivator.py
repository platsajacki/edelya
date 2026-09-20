from collections.abc import Callable
from dataclasses import dataclass

from django.db.models import QuerySet

from apps.dishes.models import Dish, Ingredient
from apps.shopping.models import ShoppingList
from core.base.exceptions import IngredientInUseError
from core.base.services import BaseService

INGREDIENT_IN_USE_DETAIL = 'Ingredient is used and cannot be deleted.'
USAGE_PREVIEW_LIMIT = 5


@dataclass
class IngredientDeactivator(BaseService[None]):
    instance: Ingredient

    def get_validators(self) -> list[Callable]:
        return super().get_validators() + [self.validate_not_in_use]

    def get_dishes(self) -> QuerySet[Dish]:
        return Dish.objects.filter(is_active=True, dish_ingredients__ingredient=self.instance).distinct()

    def get_shopping_lists(self) -> QuerySet[ShoppingList]:
        return ShoppingList.objects.filter(items__ingredient=self.instance).distinct()

    def serialize_dish(self, dish: Dish) -> dict[str, str]:
        return {'id': str(dish.id), 'name': dish.name}

    def serialize_shopping_list(self, shopping_list: ShoppingList) -> dict[str, str]:
        return {
            'id': str(shopping_list.id),
            'name': shopping_list.name,
            'date_from': shopping_list.date_from.isoformat(),
            'date_to': shopping_list.date_to.isoformat(),
        }

    def build_detail(self, dishes: QuerySet[Dish], shopping_lists: QuerySet[ShoppingList]) -> dict:
        return {
            'detail': INGREDIENT_IN_USE_DETAIL,
            'dishes': [self.serialize_dish(dish) for dish in dishes[:USAGE_PREVIEW_LIMIT]],
            'dishes_total': dishes.count(),
            'shopping_lists': [
                self.serialize_shopping_list(shopping_list) for shopping_list in shopping_lists[:USAGE_PREVIEW_LIMIT]
            ],
            'shopping_lists_total': shopping_lists.count(),
        }

    def validate_not_in_use(self) -> None:
        dishes = self.get_dishes()
        shopping_lists = self.get_shopping_lists()
        if not dishes.exists() and not shopping_lists.exists():
            return
        raise IngredientInUseError(self.build_detail(dishes, shopping_lists))

    def act(self) -> None:
        self.instance.deactivate()
