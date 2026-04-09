from django.db.models import F, OrderBy, QuerySet

from django_filters import rest_framework as filters

from apps.dishes.models import Dish, DishCategory


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
    owened_first = filters.BooleanFilter(method='order_owned_first')
    only_owned = filters.BooleanFilter(field_name='owner_id', lookup_expr='isnull', exclude=True)
    only_global = filters.BooleanFilter(field_name='owner_id', lookup_expr='isnull')

    class Meta:
        model = Dish
        fields = {
            'id': ['exact', 'in'],
            'name': ['exact', 'icontains', 'in'],
            'created_at': ['exact', 'lte', 'gte'],
            'updated_at': ['exact', 'lte', 'gte'],
        }

    def order_owned_first(self, queryset: QuerySet, name: str, value: bool) -> QuerySet:
        if value:
            return queryset.order_by(OrderBy(F('owner_id'), nulls_last=True))
        return queryset
