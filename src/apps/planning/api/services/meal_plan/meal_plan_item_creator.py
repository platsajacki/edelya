from dataclasses import dataclass
from dataclasses import field as dc_field

from django.db import transaction
from django.db.models import QuerySet
from rest_framework import status
from rest_framework.response import Response

from apps.planning.api.serializers.meal_plan import MealPlanItemSerializer
from apps.planning.api.services.base import BaseMealPlanItemCreator
from apps.planning.models import MealPlanItem
from core.base.services import BaseViewSetService


@dataclass
class MealPlanItemCreator(BaseViewSetService, BaseMealPlanItemCreator):
    queryset: QuerySet = dc_field(default_factory=MealPlanItem.objects.none)

    def create_meal_plan_items(self) -> list[MealPlanItem]:
        return self.create_meal_plan_items_by_dates(
            owner=self.validated_data['owner'],
            dish=self.validated_data['dish'],
            eat_dates=self.validated_data['eat_dates'],
            is_manual=True,
        )

    @transaction.atomic
    def act(self) -> None:
        plans = self.create_meal_plan_items()
        self.serializer.instance_list = self.queryset.filter(id__in=[plan.id for plan in plans])
        data = MealPlanItemSerializer(self.serializer.instance_list, many=True).data
        return Response(data, status=status.HTTP_201_CREATED)
