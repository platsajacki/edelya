from django_filters import rest_framework as filters

from apps.shopping.models import ShoppingList, ShoppingListItem


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


class ShoppingListItemFilter(filters.FilterSet):
    ingredient = filters.CharFilter(field_name='ingredient__name', lookup_expr='icontains')
    ordering = filters.OrderingFilter(
        fields=(
            ('created_at', 'created_at'),
            ('updated_at', 'updated_at'),
            ('amount', 'amount'),
            ('is_checked', 'is_checked'),
            ('checked_at', 'checked_at'),
            ('ingredient__name', 'ingredient__name'),
            ('ingredient__category__name', 'ingredient__category__name'),
            ('position', 'position'),
        ),
        field_labels={
            'created_at': 'Created at',
            'updated_at': 'Updated at',
            'amount': 'Amount',
            'is_checked': 'Is checked',
            'checked_at': 'Checked at',
            'ingredient__name': 'Ingredient name',
            'ingredient__category__name': 'Ingredient category name',
            'position': 'Position',
        },
    )

    class Meta:
        model = ShoppingListItem
        fields = {
            'id': ['exact', 'in'],
            'amount': ['exact', 'lte', 'gte'],
            'is_checked': ['exact'],
            'checked_at': ['exact', 'lte', 'gte'],
            'created_at': ['exact', 'lte', 'gte'],
            'updated_at': ['exact', 'lte', 'gte'],
        }
