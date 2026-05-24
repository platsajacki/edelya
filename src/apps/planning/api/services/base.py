from datetime import date

from apps.dishes.models.dishes import Dish
from apps.planning.contstants import POSITION_STEP
from apps.planning.models import CookingEvent, MealPlanItem
from apps.users.models import User
from core.utils import get_random_color


class BaseMealPlanItemCreator:
    def get_color_for_meal_plan_item(
        self, cooking_event: CookingEvent | None, owner: User, eat_dates: list[date]
    ) -> str:
        if cooking_event:
            return cooking_event.color
        existing_colors = MealPlanItem.objects.get_existing_colors_for_dates(
            owner=owner,
            eat_dates=eat_dates,
        )
        return get_random_color(existing_colors)

    def create_meal_plan_items_by_dates(
        self, owner: User, dish: Dish, eat_dates: list[date], is_manual: bool, cooking_event: CookingEvent | None = None
    ) -> list[MealPlanItem]:
        position_by_date = MealPlanItem.objects.get_max_position_for_user_and_dates(
            user=owner,
            dates=eat_dates,
            position_step=POSITION_STEP,
        )
        meal_plan_items = []
        color = self.get_color_for_meal_plan_item(cooking_event, owner, eat_dates)
        for _date in eat_dates:
            item = MealPlanItem(
                owner=owner,
                date=_date,
                dish=dish,
                position=position_by_date[_date],
                is_manual=is_manual,
                cooking_event=cooking_event,
                color=color,
            )
            position_by_date[_date] += POSITION_STEP
            meal_plan_items.append(item)
        return MealPlanItem.objects.bulk_create(meal_plan_items)
