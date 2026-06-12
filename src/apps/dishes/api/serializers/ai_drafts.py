from typing import cast

from rest_framework import serializers

from apps.dishes.data_types import DishPayloadData
from apps.dishes.models import DishAIDraft
from apps.dishes.models.validators import dish_payload_validator


class DishAIDraftSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    source_text = serializers.CharField(min_length=10, max_length=10_000)

    class Meta:
        model = DishAIDraft
        fields = [
            'id',
            'owner',
            'source_text',
            'status',
            'payload',
            'created_dish',
            'validation_errors',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'status',
            'payload',
            'created_dish',
            'validation_errors',
            'created_at',
            'updated_at',
        ]


class DishAIDraftCreateDishSerializer(serializers.Serializer):
    payload = serializers.JSONField()

    def validate_payload(self, value: dict) -> DishPayloadData:
        try:
            dish_payload_validator(value)
        except serializers.ValidationError as e:
            raise serializers.ValidationError(e.message) from e
        return cast(DishPayloadData, value)
