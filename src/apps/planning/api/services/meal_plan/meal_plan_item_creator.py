from dataclasses import dataclass
from dataclasses import field as dc_field

from django.db import transaction
from django.db.models import QuerySet
from rest_framework import status
from rest_framework.response import Response

from apps.planning.api.serializers.meal_plan import MealPlanItemSerializer
from apps.planning.models import MealPlanItem
from core.base.services import BaseViewSetService

POSITION_STEP = 100


@dataclass
class MealPlanItemCreator(BaseViewSetService):
    queryset: QuerySet = dc_field(default_factory=MealPlanItem.objects.none)

    def create_meal_plan_items(self) -> list[MealPlanItem]:
        position = self.validated_data.get('position', POSITION_STEP)
        meal_plan_items = [
            MealPlanItem(
                owner=self.validated_data['owner'],
                date=_date,
                dish=self.validated_data['dish'],
                position=position + index * POSITION_STEP,
                is_manual=True,
            )
            for index, _date in enumerate(self.validated_data['eat_dates'])
        ]
        return MealPlanItem.objects.bulk_create(meal_plan_items, ignore_conflicts=True)

    @transaction.atomic
    def act(self) -> None:
        plans = self.create_meal_plan_items()
        self.serializer.instance_list = self.queryset.filter(id__in=[plan.id for plan in plans])
        data = MealPlanItemSerializer(self.serializer.instance_list, many=True).data
        return Response(data, status=status.HTTP_201_CREATED)
