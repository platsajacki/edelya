from django.db.models import QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet

from apps.planning.api.schemas import MealPlanItemViewSetSchema
from apps.planning.api.serializers.meal_plan import (
    MealPlanItemCreateSerializer,
    MealPlanItemSerializer,
    MealPlanItemUpdateSerializer,
)
from apps.planning.models import MealPlanItem
from core.base.decorators import extend_schema_view_from_class
from core.base.permissions import OwnerObjectPermission


@extend_schema_view_from_class(MealPlanItemViewSetSchema)
class MealPlanItemViewSet(ModelViewSet):
    queryset = MealPlanItem.objects.none()
    permission_classes = [IsAuthenticated & OwnerObjectPermission]
    http_method_names = ['post', 'patch', 'delete']
    lookup_url_kwarg = 'meal_plan_item_id'

    def get_serializer_class(self) -> type[ModelSerializer]:
        if self.action == 'create':
            return MealPlanItemCreateSerializer
        elif self.action in {'update', 'partial_update'}:
            return MealPlanItemUpdateSerializer
        return MealPlanItemSerializer

    def get_queryset(self) -> QuerySet[MealPlanItem]:
        if self.request.user.is_authenticated:
            return MealPlanItem.objects.full_info_for_user(self.request.user)
        return MealPlanItem.objects.none()
