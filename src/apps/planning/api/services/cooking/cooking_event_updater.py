from datetime import date, timedelta

from django.db import transaction

from apps.planning.api.services.cooking.base import CookingEventBaseService
from apps.planning.models import CookingEvent, MealPlanItem


class CookingEventUpdater(CookingEventBaseService):
    def shift_meal_plan_item_dates(
        self, cooking_event: CookingEvent, old_start_eating_date: date, meal_plan_items: list[MealPlanItem]
    ) -> None:
        date_diff = cooking_event.start_eating_date - old_start_eating_date
        for meal_plan_item in meal_plan_items:
            meal_plan_item.date += date_diff
        MealPlanItem.objects.bulk_update(meal_plan_items, ['date'])

    def sync_meal_plan_items(
        self, cooking_event: CookingEvent, old_duration_days: int, meal_plan_items: list[MealPlanItem]
    ) -> None:
        duration_days_diff = cooking_event.duration_days - old_duration_days
        sorted_meal_plan_items = sorted(meal_plan_items, key=lambda x: x.date)
        if duration_days_diff > 0:
            max_date = sorted_meal_plan_items[-1].date
            missing_dates = self.get_meal_plan_item_dates(max_date + timedelta(days=1), duration_days_diff)
            self.create_meal_plan_items(cooking_event, missing_dates)
        else:
            duration_days_abs = abs(duration_days_diff)
            meal_plan_items_to_delete = sorted_meal_plan_items[-duration_days_abs:]
            MealPlanItem.objects.filter(id__in=[item.id for item in meal_plan_items_to_delete]).delete()

    @transaction.atomic
    def act(self) -> None:
        old_start_eating_date = self.serializer.instance.start_eating_date
        old_duration_days = self.serializer.instance.duration_days
        cooking_event = self.serializer.save()
        meal_plan_items = list(MealPlanItem.objects.filter(cooking_event=cooking_event))
        if not meal_plan_items:
            self.create_meal_plan_items(cooking_event, self.get_meal_plan_item_dates_by_cooking_event(cooking_event))
            return
        if cooking_event.start_eating_date != old_start_eating_date:
            self.shift_meal_plan_item_dates(cooking_event, old_start_eating_date, meal_plan_items)
        if cooking_event.duration_days != old_duration_days:
            self.sync_meal_plan_items(cooking_event, old_duration_days, meal_plan_items)
