from django.db import transaction

from apps.planning.api.services.cooking.base import CookingEventBaseService


class CookingEventCreator(CookingEventBaseService):
    @transaction.atomic
    def act(self) -> None:
        eat_dates = self.serializer.validated_data['eat_dates']
        owner = self.serializer.validated_data['owner']
        color = self.get_color_for_cooking_event(owner=owner, eat_dates=eat_dates)
        cooking_event = self.serializer.save(color=color)
        self.create_meal_plan_items(cooking_event, eat_dates)
