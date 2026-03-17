from datetime import date

from apps.dishes.models.dishes import Dish
from apps.planning.contstants import POSITION_STEP
from apps.planning.models import CookingEvent, MealPlanItem
from apps.users.models import User


class BaseMealPlanItemCreator:
    def create_meal_plan_items_by_dates(
        self, owner: User, dish: Dish, eat_dates: list[date], is_manual: bool, cooking_event: CookingEvent | None = None
    ) -> list[MealPlanItem]:
        position_by_date = MealPlanItem.objects.get_max_position_for_user_and_dates(
            user=owner,
            dates=eat_dates,
            position_step=POSITION_STEP,
        )
        meal_plan_items = []
        for _date in eat_dates:
            item = MealPlanItem(
                owner=owner,
                date=_date,
                dish=dish,
                position=position_by_date[_date],
                is_manual=is_manual,
                cooking_event=cooking_event,
            )
            position_by_date[_date] += POSITION_STEP
            meal_plan_items.append(item)
        return MealPlanItem.objects.bulk_create(meal_plan_items)
