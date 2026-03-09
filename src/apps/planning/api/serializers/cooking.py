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
