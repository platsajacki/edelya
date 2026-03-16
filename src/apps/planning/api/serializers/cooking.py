from copy import deepcopy

from rest_framework.exceptions import ValidationError
from rest_framework.fields import CurrentUserDefault, DateField, HiddenField, ListField
from rest_framework.serializers import ModelSerializer

from apps.dishes.api.serializers.dishes import DishReadSerializer
from apps.planning.models import CookingEvent, MealPlanItem


class LightMealPlanItemSerializer(ModelSerializer):
    class Meta:
        model = MealPlanItem
        fields = [
            'id',
            'dish',
            'date',
            'cooking_event',
            'position',
            'is_manual',
            'created_at',
            'updated_at',
        ]


class CookingEventSerializer(ModelSerializer):
    dish = DishReadSerializer(read_only=True)
    owner = HiddenField(default=CurrentUserDefault())
    meal_plan_items = LightMealPlanItemSerializer(many=True, read_only=True)

    class Meta:
        model = CookingEvent
        fields = [
            'id',
            'dish',
            'owner',
            'cooking_date',
            'notes',
            'created_at',
            'updated_at',
            'meal_plan_items',
        ]


class CookingEventWriteSerializer(ModelSerializer):
    owner = HiddenField(default=CurrentUserDefault())
    eat_dates = ListField(child=DateField(), write_only=True)

    class Meta:
        model = CookingEvent
        fields = [
            'id',
            'dish',
            'owner',
            'cooking_date',
            'eat_dates',
            'notes',
            'created_at',
            'updated_at',
        ]

    def validate(self, attrs: dict) -> dict:
        cooking_date = attrs.get('cooking_date', getattr(self.instance, 'cooking_date', None))
        eat_dates = attrs.get('eat_dates', [])
        if cooking_date and eat_dates and any(eat_date < cooking_date for eat_date in eat_dates):
            raise ValidationError('All eat_dates must be on or after cooking_date.')
        return attrs

    def create(self, validated_data: dict) -> CookingEvent:
        data_for_model = deepcopy(validated_data)
        del data_for_model['eat_dates']
        return super().create(data_for_model)

    def to_representation(self, instance: CookingEvent) -> dict:
        return CookingEventSerializer(instance).data
