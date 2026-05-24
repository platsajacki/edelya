from typing import Any

from django.db.models import QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet

from apps.planning.api.schemas import MealPlanItemViewSetSchema
from apps.planning.api.serializers.meal_plan import (
    MealPlanItemCreateSerializer,
    MealPlanItemSerializer,
    MealPlanItemUpdateSerializer,
)
from apps.planning.api.services.meal_plan.meal_plan_item_creator import MealPlanItemCreator
from apps.planning.models import MealPlanItem
from core.base.decorators import extend_schema_view_from_class
from core.base.permissions import CanUseBaseFeatures, HasActiveTrial, OwnerObjectPermission


@extend_schema_view_from_class(MealPlanItemViewSetSchema)
class MealPlanItemViewSet(ModelViewSet):
    queryset = MealPlanItem.objects.none()
    permission_classes = [IsAuthenticated & OwnerObjectPermission & (HasActiveTrial | CanUseBaseFeatures)]
    http_method_names = ['post', 'patch', 'delete']
    lookup_url_kwarg = 'meal_plan_item_id'

    def get_serializer_class(self) -> type[ModelSerializer]:
        if self.action == 'create':
            return MealPlanItemCreateSerializer
        elif self.action == 'partial_update':
            return MealPlanItemUpdateSerializer
        return MealPlanItemSerializer

    def get_queryset(self) -> QuerySet[MealPlanItem]:
        if self.request.user.is_authenticated:
            return MealPlanItem.objects.full_info_for_user(self.request.user)
        return MealPlanItem.objects.none()

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return MealPlanItemCreator(self.get_serializer(data=request.data), queryset=self.get_queryset())()
