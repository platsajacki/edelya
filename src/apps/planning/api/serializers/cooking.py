from rest_framework.exceptions import ValidationError
from rest_framework.fields import CurrentUserDefault, HiddenField
from rest_framework.serializers import ModelSerializer

from apps.dishes.api.serializers.dishes import DishReadSerializer
from apps.planning.models import CookingEvent


class CookingEventSerializer(ModelSerializer):
    dish = DishReadSerializer(read_only=True)
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
        if attrs['start_eating_date'] < attrs['cooking_date']:
            raise ValidationError('Date when eating starts cannot be earlier than cooking date')
        return attrs
