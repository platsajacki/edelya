from datetime import date

from apps.planning.api.services.base import BaseMealPlanItemCreator
from apps.planning.models import CookingEvent, MealPlanItem
from apps.users.models import User
from core.base.services import BaseViewSetPerformService
from core.utils import get_random_color


class CookingEventBaseService(BaseViewSetPerformService, BaseMealPlanItemCreator):
    def get_color_for_cooking_event(self, owner: User, eat_dates: list[date]) -> str:
        meal_existing_colors = MealPlanItem.objects.get_existing_colors_for_dates(owner=owner, eat_dates=eat_dates)
        cooking_existing_colors = CookingEvent.objects.get_existing_colors_for_dates(owner=owner, eat_dates=eat_dates)
        existing_colors = list(set(meal_existing_colors + cooking_existing_colors))
        return get_random_color(existing_colors)

    def create_meal_plan_items(self, cooking_event: CookingEvent, dates: list[date]) -> list[MealPlanItem]:
        return self.create_meal_plan_items_by_dates(
            owner=cooking_event.owner,
            dish=cooking_event.dish,
            eat_dates=dates,
            is_manual=False,
            cooking_event=cooking_event,
        )
