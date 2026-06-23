from typing import TYPE_CHECKING

from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q, Value
from django.db.models.functions import Lower, Replace

from core.base.managers import ActiveManager, ActiveQuerySet, NameSearchManager, NameSearchQuerySet
from core.utils import normalize_name

if TYPE_CHECKING:
    from apps.dishes.models import Ingredient, IngredientCategory  # noqa: F401
    from apps.users.models import User


class IngredientCategoryQueryset(ActiveQuerySet['IngredientCategory']):
    def get_by_names(self, names: list[str]) -> IngredientCategoryQueryset:
        names = [normalize_name(name).lower() for name in names]
        return self.annotate(name_lower=Lower('name')).filter(name_lower__in=names)


class IngredientCategoryManager(ActiveManager['IngredientCategory', IngredientCategoryQueryset]):
    def get_queryset_class(self) -> type[IngredientCategoryQueryset]:
        return IngredientCategoryQueryset

    def get_by_names(self, names: list[str]) -> IngredientCategoryQueryset:
        return self.get_queryset().get_by_names(names)


class IngredientQueryset(NameSearchQuerySet['Ingredient']):
    def for_user(self, user: User) -> IngredientQueryset:
        return self.actived().filter(Q(owner__isnull=True) | Q(owner=user))

    def with_category(self) -> IngredientQueryset:
        return self.select_related('category')

    def get_by_names(self, names: list[str]) -> IngredientQueryset:
        names = [normalize_name(name).lower() for name in names]
        return self.annotate(name_lower=Lower('name')).filter(name_lower__in=names)

    def get_by_names_for_user(self, names: list[str], user: User) -> IngredientQueryset:
        return self.for_user(user).get_by_names(names)

    def search_by_name(self, query: str, threshold: float = 0.8, limit: int = 3) -> IngredientQueryset:
        query = normalize_name(query).lower()
        normalized_db_name = Replace(
            Lower('name'),
            Value('ё'),
            Value('е'),
        )
        return (
            self.annotate(similarity=TrigramSimilarity(normalized_db_name, query))
            .filter(similarity__gte=threshold)
            .order_by('-similarity')[:limit]
        )

    def search_by_name_for_user(
        self, query: str, user: User, threshold: float = 0.8, limit: int = 3
    ) -> IngredientQueryset:
        return self.for_user(user).search_by_name(query, threshold, limit)


class IngredientManager(NameSearchManager['Ingredient', IngredientQueryset]):
    def get_queryset_class(self) -> type[IngredientQueryset]:
        return IngredientQueryset

    def for_user(self, user: User) -> IngredientQueryset:
        return self.get_queryset().for_user(user).with_category()

    def with_category(self) -> IngredientQueryset:
        return self.get_queryset().with_category()

    def get_by_names(self, names: list[str]) -> IngredientQueryset:
        return self.get_queryset().get_by_names(names)

    def get_by_names_for_user(self, names: list[str], user: User) -> IngredientQueryset:
        return self.get_queryset().get_by_names_for_user(names, user)

    def search_by_name(self, query: str, threshold: float = 0.8, limit: int = 3) -> IngredientQueryset:
        return self.get_queryset().search_by_name(query, threshold, limit)

    def search_by_name_for_user(
        self, query: str, user: User, threshold: float = 0.8, limit: int = 3
    ) -> IngredientQueryset:
        return self.get_queryset().search_by_name_for_user(query, user, threshold, limit)
