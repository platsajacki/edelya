from datetime import date, timedelta

from apps.planning.models import CookingEvent, MealPlanItem
from core.base.services import BaseViewSetPerformService


class CookingEventBaseService(BaseViewSetPerformService):
    def get_meal_plan_item_dates(self, start_date: date, duration_days: int) -> list[date]:
        return [start_date + timedelta(days=day) for day in range(duration_days)]

    def get_meal_plan_item_dates_by_cooking_event(self, cooking_event: CookingEvent) -> list[date]:
        return self.get_meal_plan_item_dates(cooking_event.start_eating_date, cooking_event.duration_days)

    def create_meal_plan_items(self, cooking_event: CookingEvent, dates: list[date]) -> list[MealPlanItem]:
        meal_plan_items = []
        for _date in dates:
            meal_plan_item = MealPlanItem(
                owner=cooking_event.owner,
                date=_date,
                dish=cooking_event.dish,
                cooking_event=cooking_event,
                is_manual=False,
            )
            meal_plan_items.append(meal_plan_item)
        return MealPlanItem.objects.bulk_create(meal_plan_items, ignore_conflicts=True)
