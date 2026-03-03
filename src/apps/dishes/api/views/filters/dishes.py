from django_filters import rest_framework as filters

from apps.dishes.models import DishCategory


class DishCategoryFilter(filters.FilterSet):
    ordering = filters.OrderingFilter(
        fields=(
            ('id', 'id'),
            ('name', 'name'),
            ('created_at', 'created_at'),
            ('updated_at', 'updated_at'),
        )
    )

    class Meta:
        model = DishCategory
        fields = {
            'id': ['exact', 'in'],
            'name': ['exact', 'icontains', 'in'],
            'created_at': ['exact', 'lte', 'gte'],
            'updated_at': ['exact', 'lte', 'gte'],
        }


class DishFilter(filters.FilterSet):
    category = filters.UUIDFilter(field_name='category__id')

    class Meta:
        model = DishCategory
        fields = {
            'id': ['exact', 'in'],
            'name': ['exact', 'icontains', 'in'],
            'category': ['exact', 'in'],
            'created_at': ['exact', 'lte', 'gte'],
            'updated_at': ['exact', 'lte', 'gte'],
        }
