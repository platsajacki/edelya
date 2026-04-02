from typing import Any

from django.db.models import QuerySet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.shopping.api.schemas import ShoppingListViewSetSchema
from apps.shopping.api.serializers.shopping_list import ShoppingListSerializer
from apps.shopping.api.services.shopping_list_recalculater import (
    ShoppingListInstanceRecalculater,
    ShoppingListPerformRecalculater,
)
from apps.shopping.api.views.filters.sopping_list import ShoppingListFilter
from apps.shopping.models import ShoppingList
from apps.users.models import User
from core.base.decorators import extend_schema_view_from_class
from core.base.permissions import OwnerObjectPermission


@extend_schema_view_from_class(ShoppingListViewSetSchema)
class ShoppingListViewSet(ModelViewSet):
    queryset = ShoppingList.objects.none()
    serializer_class = ShoppingListSerializer
    permission_classes = [IsAuthenticated, OwnerObjectPermission]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    lookup_url_kwarg = 'shopping_list_id'
    filterset_class = ShoppingListFilter

    def get_queryset(self) -> QuerySet[ShoppingList]:
        if isinstance(self.request.user, User):
            return ShoppingList.objects.for_user(self.request.user)
        return ShoppingList.objects.none()

    def perform_create(self, serializer: ShoppingListSerializer) -> None:
        ShoppingListPerformRecalculater(serializer=serializer)()

    def perform_update(self, serializer: ShoppingListSerializer) -> None:
        ShoppingListPerformRecalculater(serializer=serializer, not_recalculated_fields={'name'})()

    @action(detail=True, methods=['post'], url_path='recalculate')
    def recalculate(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        shopping_list = self.get_object()
        ShoppingListInstanceRecalculater(instance=shopping_list)()
        return Response({'detail': 'Shopping list recalculated successfully.'}, status=status.HTTP_200_OK)


# class ShoppingListItemViewSet(ModelViewSet):
#     queryset = ShoppingListItem.objects.none()
#     serializer_class = ShoppingListItemSerializer
#     permission_classes = [IsAuthenticated, OwnerObjectPermission]
#     http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
#     lookup_url_kwarg = 'shopping_list_item_id'
#     filterset_class = None  # TODO: add filterset for shopping list items

#     def get_queryset(self) -> QuerySet[ShoppingListItem]: ...
