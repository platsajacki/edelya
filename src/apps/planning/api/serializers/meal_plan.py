from rest_framework.exceptions import ValidationError
from rest_framework.fields import CurrentUserDefault, DateField, HiddenField, ListField
from rest_framework.serializers import ModelSerializer, Serializer

from apps.dishes.api.serializers.dishes import DishReadSerializer
from apps.planning.api.serializers.cooking import CookingEventSerializer
from apps.planning.models import MealPlanItem


class MealPlanItemSerializer(ModelSerializer):
    dish = DishReadSerializer(read_only=True)

    class Meta:
        model = MealPlanItem
        fields = [
            'id',
            'dish',
            'owner',
            'date',
            'cooking_event',
            'position',
            'is_manual',
            'color',
            'created_at',
            'updated_at',
        ]


class WeekDishesSerializer(Serializer):
    start_week = DateField()
    end_week = DateField()
    meal_plan_items = MealPlanItemSerializer(many=True)
    cooking_events = CookingEventSerializer(many=True)


class EatDatesSerializer(ModelSerializer):
    eat_dates = ListField(child=DateField(), write_only=True, allow_empty=False)

    class Meta:
        model = MealPlanItem
        fields = [
            'id',
            'eat_dates',
        ]

    def validate(self, attrs: dict) -> dict:
        eat_date = attrs.get('date', getattr(self.instance, 'date', None))
        eat_dates = attrs.get('eat_dates', [])
        if eat_date and eat_dates and any(d < eat_date for d in eat_dates):
            raise ValidationError(
                'All eat_dates must be greater than or equal to the current date of the meal plan item.'
            )
        return attrs


class MealPlanItemCreateSerializer(EatDatesSerializer):
    owner = HiddenField(default=CurrentUserDefault())
    is_manual = HiddenField(default=True)

    class Meta:
        model = MealPlanItem
        fields = [
            'id',
            'dish',
            'owner',
            'eat_dates',
            'cooking_event',
            'position',
            'is_manual',
            'color',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'cooking_event',
            'color',
            'created_at',
            'updated_at',
        ]


class MealPlanItemUpdateSerializer(ModelSerializer):
    class Meta:
        model = MealPlanItem
        fields = [
            'id',
            'dish',
            'owner',
            'date',
            'cooking_event',
            'position',
            'is_manual',
            'color',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'owner',
            'cooking_event',
            'is_manual',
            'color',
            'created_at',
            'updated_at',
        ]

    def validate_date(self, value: DateField) -> DateField:
        if self.instance and self.instance.cooking_event and value < self.instance.cooking_event.cooking_date:
            raise ValidationError('Date must be on or after the cooking date of the associated cooking event.')
        return value
