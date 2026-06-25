from typing import Any

from django.db.models import QuerySet
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.dishes.api.schemas import DishAIDraftViewSetSchema
from apps.dishes.api.serializers.ai_drafts import DishAIDraftCreateDishSerializer, DishAIDraftSerializer
from apps.dishes.api.services.ai_draft_creator import AIDraftCreator
from apps.dishes.api.services.ai_draft_dish_creator import AIDraftDishCreator
from apps.dishes.api.views.filters.ai_drafts import DishAIDraftFilter
from apps.dishes.models import Dish, DishAIDraft
from apps.users.models import User
from core.base.decorators import extend_schema_view_from_class
from core.base.permissions import CanCreateAIRecipes, OwnerObjectPermission


@extend_schema_view_from_class(DishAIDraftViewSetSchema)
class DishAIDraftViewSet(ModelViewSet):
    queryset = DishAIDraft.objects.none()
    serializer_class = DishAIDraftSerializer
    permission_classes = [IsAuthenticated & OwnerObjectPermission]
    http_method_names = ['get', 'post', 'head', 'options']
    lookup_url_kwarg = 'draft_id'
    filterset_class = DishAIDraftFilter

    def get_queryset(self) -> QuerySet[DishAIDraft]:
        if isinstance(self.request.user, User):
            return DishAIDraft.objects.for_user(self.request.user)
        return DishAIDraft.objects.none()

    def get_permissions(self) -> list[BasePermission]:
        if self.action == 'create':
            return [IsAuthenticated(), CanCreateAIRecipes()]
        return super().get_permissions()

    def perform_create(self, serializer: DishAIDraftSerializer) -> None:
        AIDraftCreator(serializer=serializer)()

    @action(detail=True, methods=['post'], url_path='create-dish')
    def create_dish(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        draft = self.get_object()
        serializer = DishAIDraftCreateDishSerializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        return AIDraftDishCreator(
            serializer=serializer,
            draft=draft,
            queryset=Dish.objects.for_user(request.user),
        )()
