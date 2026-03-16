from django.db import transaction

from apps.planning.api.services.cooking.base import CookingEventBaseService


class CookingEventCreator(CookingEventBaseService):
    @transaction.atomic
    def act(self) -> None:
        cooking_event = self.serializer.save()
        self.create_meal_plan_items(cooking_event, self.serializer.validated_data['eat_dates'])
