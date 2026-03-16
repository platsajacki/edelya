from datetime import date

from apps.planning.models import CookingEvent, MealPlanItem
from core.base.services import BaseViewSetPerformService


class CookingEventBaseService(BaseViewSetPerformService):
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
