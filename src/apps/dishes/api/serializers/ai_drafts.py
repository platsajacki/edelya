from rest_framework import serializers

from apps.dishes.models import DishAIDraft


class DishAIDraftSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    source_text = serializers.CharField(min_length=10, max_length=20_000)

    class Meta:
        model = DishAIDraft
        fields = [
            'id',
            'owner',
            'source_text',
            'status',
            'payload',
            'validation_errors',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'status',
            'payload',
            'validation_errors',
            'created_at',
            'updated_at',
        ]
