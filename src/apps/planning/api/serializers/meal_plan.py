from rest_framework.serializers import DateField, ModelSerializer, Serializer

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
