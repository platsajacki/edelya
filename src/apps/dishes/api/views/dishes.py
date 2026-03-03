from django.db.models import QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.dishes.api.schemas import DishCategoryViewSetSchema
from apps.dishes.api.serializers.dishes import DishCategorySerializer, DishSerializer
from apps.dishes.api.views.filters.dishes import DishCategoryFilter, DishFilter
from apps.dishes.models import Dish, DishCategory
from core.base.decorators import extend_schema_view_from_class
from core.base.permissions import OwnerObjectPermission


@extend_schema_view_from_class(DishCategoryViewSetSchema)
class DishCategoryViewSet(ReadOnlyModelViewSet):
    queryset = DishCategory.objects.actived()
    serializer_class = DishCategorySerializer
    permission_classes = [IsAuthenticated]
    filterset_class = DishCategoryFilter
    lookup_url_kwarg = 'dish_category_id'


class DishViewSet(ModelViewSet):
    queryset = Dish.objects.none()
    serializer_class = DishSerializer
    permission_classes = [IsAuthenticated & OwnerObjectPermission]
    filterset_class = DishFilter
    lookup_url_kwarg = 'dish_id'

    def get_queryset(self) -> QuerySet[Dish]:
        if self.request.user.is_authenticated:
            return Dish.objects.for_user(self.request.user).with_category().with_ingredients()
        return Dish.objects.none()

    def perform_destroy(self, instance: Dish) -> None:
        instance.deactivate()
