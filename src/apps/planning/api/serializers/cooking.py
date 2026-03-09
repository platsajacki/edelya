from rest_framework.exceptions import ValidationError
from rest_framework.fields import CurrentUserDefault, HiddenField
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
            'duration_days',
            'start_eating_date',
            'notes',
            'created_at',
            'updated_at',
            'meal_plan_items',
        ]


class CookingEventWriteSerializer(ModelSerializer):
    owner = HiddenField(default=CurrentUserDefault())

    class Meta:
        model = CookingEvent
        fields = [
            'id',
            'dish',
            'owner',
            'cooking_date',
            'duration_days',
            'start_eating_date',
            'notes',
            'created_at',
            'updated_at',
        ]

    def validate(self, attrs: dict) -> dict:
        start_eating_date = attrs.get('start_eating_date', getattr(self.instance, 'start_eating_date', None))
        cooking_date = attrs.get('cooking_date', getattr(self.instance, 'cooking_date', None))
        if start_eating_date and cooking_date and start_eating_date < cooking_date:
            raise ValidationError('Date when eating starts cannot be earlier than cooking date')
        return attrs

    def to_representation(self, instance: CookingEvent) -> dict:
        return CookingEventSerializer(instance).data
