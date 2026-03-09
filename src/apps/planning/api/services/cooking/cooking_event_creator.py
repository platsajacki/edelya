from django.db import transaction

from apps.planning.api.services.cooking.base import CookingEventBaseService


class CookingEventCreator(CookingEventBaseService):
    @transaction.atomic
    def act(self) -> None:
        cooking_event = self.serializer.save()
        dates = self.get_meal_plan_item_dates_by_cooking_event(cooking_event)
        self.create_meal_plan_items(cooking_event, dates)
