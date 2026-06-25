from django_filters import rest_framework as filters

from apps.dishes.models import DishAIDraft


class DishAIDraftFilter(filters.FilterSet):
    ordering = filters.OrderingFilter(
        fields=(
            ('id', 'id'),
            ('status', 'status'),
            ('created_at', 'created_at'),
            ('updated_at', 'updated_at'),
        )
    )

    class Meta:
        model = DishAIDraft
        fields = {
            'id': ['exact', 'in'],
            'status': ['exact', 'in'],
            'source_text': ['exact', 'icontains'],
            'created_dish': ['exact', 'in'],
            'created_at': ['exact', 'lte', 'gte'],
            'updated_at': ['exact', 'lte', 'gte'],
        }
