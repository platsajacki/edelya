from django.db.models import QuerySet

from django_filters import rest_framework as filters

from apps.dishes.models import Ingredient, IngredientCategory
from apps.dishes.models.managers.ingredients import IngredientQueryset


class IngredientCategoryFilter(filters.FilterSet):
    ordering = filters.OrderingFilter(
        fields=(
            ('id', 'id'),
            ('name', 'name'),
            ('created_at', 'created_at'),
            ('updated_at', 'updated_at'),
        )
    )

    class Meta:
        model = IngredientCategory
        fields = {
            'id': ['exact', 'in'],
            'name': ['exact', 'icontains', 'in'],
            'created_at': ['exact', 'lte', 'gte'],
            'updated_at': ['exact', 'lte', 'gte'],
        }


class IngredientFilter(filters.FilterSet):
    category = filters.UUIDFilter(field_name='category__id')
    search = filters.CharFilter(method='filter_search')

    class Meta:
        model = Ingredient
        fields = {
            'id': ['exact', 'in'],
            'name': ['exact', 'icontains', 'in'],
            'category': ['exact', 'in'],
            'base_unit': ['exact', 'icontains', 'in'],
            'created_at': ['exact', 'lte', 'gte'],
            'updated_at': ['exact', 'lte', 'gte'],
        }

    def filter_search(self, queryset: IngredientQueryset, name: str, value: str) -> QuerySet:
        return queryset.search_by_normalized_name(value)
