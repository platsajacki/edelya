from rest_framework.serializers import ModelSerializer

from apps.subscriptions.models import Tariff


class TariffSerializer(ModelSerializer):
    class Meta:
        model = Tariff
        fields = [
            'id',
            'name',
            'price',
            'billing_period',
            'description',
            'trial_days',
            'can_use_base_features',
            'can_create_ai_recipes',
        ]
        read_only_fields = fields
