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
            'created_at',
            'updated_at',
        ]


class WeekDishesSerializer(Serializer):
    start_week = DateField()
    end_week = DateField()
    meal_plan_items = MealPlanItemSerializer(many=True)
    cooking_events = CookingEventSerializer(many=True)


class MealPlanItemCreateSerializer(ModelSerializer):
    owner = HiddenField(default=CurrentUserDefault())
    is_manual = HiddenField(default=True)
    eat_dates = ListField(child=DateField(), write_only=True, allow_empty=False)

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
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'cooking_event',
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
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'owner',
            'cooking_event',
            'is_manual',
            'created_at',
            'updated_at',
        ]
