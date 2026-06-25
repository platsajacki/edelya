from abc import abstractmethod
from typing import TYPE_CHECKING, Self

from django.apps import apps
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Manager, Model, Q, QuerySet, Value
from django.db.models.functions import Lower, Replace

from core.utils import normalize_name

if TYPE_CHECKING:
    from apps.dishes.models import DishIngredient
    from apps.planning.models import MealPlanItem

TRIGRAM_SEARCH_THRESHOLD = 0.3


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


class NameSearchQuerySet[ModelType: Model](ActiveQuerySet[ModelType]):
    def search_by_normalized_name(self, query: str, threshold: float = TRIGRAM_SEARCH_THRESHOLD) -> Self:
        query = normalize_name(query).lower()
        if not query:
            return self
        normalized_name = Replace(Lower('name'), Value('ё'), Value('е'))
        normalized_query = query.replace('ё', 'е')
        return (
            self.annotate(similarity=TrigramSimilarity(normalized_name, normalized_query))
            .filter(Q(name__icontains=query) | Q(similarity__gte=threshold))
            .order_by('-similarity', 'name')
        )


class NameSearchManager[ModelType: Model, QuerySetType: NameSearchQuerySet](ActiveManager[ModelType, QuerySetType]):
    def search_by_normalized_name(self, query: str, threshold: float = TRIGRAM_SEARCH_THRESHOLD) -> QuerySetType:
        return self.get_queryset().search_by_normalized_name(query, threshold)
