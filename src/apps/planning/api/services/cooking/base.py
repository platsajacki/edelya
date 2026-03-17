from datetime import date

from apps.planning.api.services.base import BaseMealPlanItemCreator
from apps.planning.models import CookingEvent, MealPlanItem
from core.base.services import BaseViewSetPerformService


class CookingEventBaseService(BaseViewSetPerformService, BaseMealPlanItemCreator):
    def create_meal_plan_items(self, cooking_event: CookingEvent, dates: list[date]) -> list[MealPlanItem]:
        return self.create_meal_plan_items_by_dates(
            owner=cooking_event.owner,
            dish=cooking_event.dish,
            eat_dates=dates,
            is_manual=False,
            cooking_event=cooking_event,
        )
