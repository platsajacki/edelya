from abc import abstractmethod
from typing import TYPE_CHECKING, Self

from django.apps import apps
from django.db.models import Manager, Model, QuerySet

if TYPE_CHECKING:
    from apps.dishes.models import DishIngredient
    from apps.planning.models import MealPlanItem


class BaseQuerySet[ModelType: Model](QuerySet[ModelType]):
    def get_dish_ingredient_model(self) -> DishIngredient:
        return apps.get_model('dishes', 'DishIngredient')  # type: ignore[return-value]

    def get_meal_plan_item_model(self) -> MealPlanItem:
        return apps.get_model('planning', 'MealPlanItem')  # type: ignore[return-value]


class BaseManager[ModelType: Model, QuerySetType: BaseQuerySet](Manager[ModelType]):
    @abstractmethod
    def get_queryset_class(self) -> type[QuerySetType]:
        raise NotImplementedError('Subclasses must implement get_queryset_class method')

    def get_queryset(self) -> QuerySetType:
        queryset_class = self.get_queryset_class()
        return queryset_class(self.model, using=self._db)


class ActiveQuerySet[ModelType: Model](BaseQuerySet[ModelType]):
    def actived(self) -> Self:
        return self.filter(is_active=True)


class ActiveManager[ModelType: Model, QuerySetType: ActiveQuerySet](BaseManager[ModelType, QuerySetType]):
    def actived(self) -> QuerySetType:
        return self.get_queryset().actived()
