from datetime import date

from django.db import transaction

from apps.planning.api.services.cooking.base import CookingEventBaseService
from apps.planning.models import CookingEvent, MealPlanItem


class CookingEventUpdater(CookingEventBaseService):
    def synchronize_meal_plan_items(
        self, cooking_event: CookingEvent, old_meal_plan_items: list[MealPlanItem], eat_dates: list[date]
    ) -> None:
        old_dates_set = {item.date for item in old_meal_plan_items}
        new_dates_set = set(eat_dates)
        dates_to_delete = old_dates_set - new_dates_set
        if dates_to_delete:
            MealPlanItem.objects.filter(cooking_event=cooking_event, date__in=dates_to_delete).delete()
        dates_to_create = sorted(new_dates_set - old_dates_set)
        if dates_to_create:
            self.create_meal_plan_items(cooking_event, dates_to_create)

    @transaction.atomic
    def act(self) -> None:
        meal_plan_items = list(self.serializer.instance.meal_plan_items.all())
        cooking_event = self.serializer.save()
        validated_data = self.serializer.validated_data
        if not meal_plan_items:
            self.create_meal_plan_items(cooking_event, validated_data['eat_dates'])
            return
        self.synchronize_meal_plan_items(cooking_event, meal_plan_items, validated_data['eat_dates'])
