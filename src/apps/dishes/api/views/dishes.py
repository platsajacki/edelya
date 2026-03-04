from typing import Any

from django.db import transaction
from django.db.models import QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.dishes.api.schemas import DishCategoryViewSetSchema, DishViewSetSchema
from apps.dishes.api.serializers.dishes import (
    DishCategorySerializer,
    DishReadSerializer,
    DishWriteSerializer,
)
from apps.dishes.api.services.dish_updater import DishUpdater
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


@extend_schema_view_from_class(DishViewSetSchema)
class DishViewSet(ModelViewSet):
    queryset = Dish.objects.none()
    serializer_class = DishWriteSerializer
    permission_classes = [IsAuthenticated & OwnerObjectPermission]
    filterset_class = DishFilter
    lookup_url_kwarg = 'dish_id'
    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'options']

    def get_queryset(self) -> QuerySet[Dish]:
        if self.request.user.is_authenticated:
            return Dish.objects.for_user(self.request.user)
        return Dish.objects.none()

    def get_serializer_class(self) -> type[DishReadSerializer | DishWriteSerializer]:
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return DishReadSerializer
        return DishWriteSerializer

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        return DishUpdater(
            serializer=serializer,
            dish=None,
            queryset=self.get_queryset(),
        )()

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        return DishUpdater(
            serializer=serializer,
            dish=instance,
            queryset=self.get_queryset(),
        )()

    def perform_destroy(self, instance: Dish) -> None:
        with transaction.atomic():
            instance.deactivate()
            instance.dish_ingredients.all().delete()
