from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import date

from django.contrib.auth.models import AbstractUser, AnonymousUser
from django.db.models import QuerySet
from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.response import Response

from apps.planning.api.serializers.meal_plan import WeekDishesSerializer
from apps.planning.models import CookingEvent, MealPlanItem
from apps.planning.utils import get_week_days
from apps.users.models import User
from core.base.services import BaseService


@dataclass
class WeekDishesGetter(BaseService):
    user: AbstractUser | AnonymousUser | User
    year: int
    week: int
    week_days: list[date] = dc_field(init=False)
    start_week: date = dc_field(init=False)
    end_week: date = dc_field(init=False)
    auth_user: User = dc_field(init=False)

    def get_validators(self) -> list[Callable]:
        return super().get_validators() + [
            self.validate_user,
            self.validate_week,
        ]

    def validate_week(self) -> None:
        try:
            self.week_days = get_week_days(self.year, self.week)
            self.start_week = self.week_days[0]
            self.end_week = self.week_days[-1]
        except ValueError as e:
            msg = f'Not valid year {self.year} and week {self.week}.'
            raise ValidationError(msg) from e

    def validate_user(self) -> None:
        if isinstance(self.user, User):
            self.auth_user = self.user
            return
        raise NotAuthenticated('User must be authenticated to get week dishes.')

    def get_meal_plan_items(self) -> QuerySet[MealPlanItem]:
        return MealPlanItem.objects.get_for_week(
            user=self.auth_user,
            start_week=self.start_week,
            end_week=self.end_week,
        )

    def get_cooking_events(self) -> QuerySet[CookingEvent]:
        return CookingEvent.objects.get_for_week(
            user=self.auth_user,
            start_week=self.start_week,
            end_week=self.end_week,
        )

    def act(self) -> Response:
        meal_plan_items = self.get_meal_plan_items()
        cooking_events = self.get_cooking_events()
        data = {
            'meal_plan_items': meal_plan_items,
            'cooking_events': cooking_events,
            'start_week': self.start_week,
            'end_week': self.end_week,
        }
        data_serialized = WeekDishesSerializer(data).data
        return Response(data_serialized)
