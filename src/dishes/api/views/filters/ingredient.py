from django_filters import rest_framework as filters

from dishes.models import Ingredient, IngredientCategory


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
