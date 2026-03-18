from datetime import date, timedelta

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

    def shift_meal_plan_items_dates(self, meal_plan_items: list[MealPlanItem], delta: timedelta) -> None:
        if delta == timedelta(0):
            return
        for item in meal_plan_items:
            item.date += delta
        MealPlanItem.objects.bulk_update(meal_plan_items, ['date'])

    def process_meal_plan_items(
        self, cooking_event: CookingEvent, meal_plan_items: list[MealPlanItem], old_cooking_date: date
    ) -> None:
        eat_dates = self.serializer.validated_data.get('eat_dates', [])
        got_eat_dates = bool(eat_dates)
        exist_meal_plan_items = bool(meal_plan_items)
        if got_eat_dates and exist_meal_plan_items:
            self.synchronize_meal_plan_items(cooking_event, meal_plan_items, eat_dates)
        elif got_eat_dates and not exist_meal_plan_items:
            self.create_meal_plan_items(cooking_event, eat_dates)
        elif not got_eat_dates and exist_meal_plan_items:
            cooking_date_delta = cooking_event.cooking_date - old_cooking_date
            self.shift_meal_plan_items_dates(meal_plan_items, cooking_date_delta)

    @transaction.atomic
    def act(self) -> None:
        meal_plan_items = list(self.serializer.instance.meal_plan_items.all())
        old_cooking_date = self.serializer.instance.cooking_date
        cooking_event = self.serializer.save()
        self.process_meal_plan_items(cooking_event, meal_plan_items, old_cooking_date)
