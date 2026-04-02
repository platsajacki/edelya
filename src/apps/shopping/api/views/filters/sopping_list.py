from django_filters import rest_framework as filters

from apps.shopping.models import ShoppingList


class ShoppingListFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    ordering = filters.OrderingFilter(
        fields=(
            ('created_at', 'created_at'),
            ('updated_at', 'updated_at'),
            ('name', 'name'),
            ('date_from', 'date_from'),
            ('date_to', 'date_to'),
        ),
        field_labels={
            'created_at': 'Created at',
            'updated_at': 'Updated at',
            'name': 'Name',
            'date_from': 'Date from',
            'date_to': 'Date to',
        },
    )

    class Meta:
        model = ShoppingList
        fields = {
            'id': ['exact', 'in'],
            'name': ['exact', 'icontains', 'in'],
            'date_from': ['exact', 'lte', 'gte'],
            'date_to': ['exact', 'lte', 'gte'],
            'created_at': ['exact', 'lte', 'gte'],
            'updated_at': ['exact', 'lte', 'gte'],
        }
