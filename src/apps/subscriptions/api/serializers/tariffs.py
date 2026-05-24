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
            'soon',
            'is_trial_tariff',
            'sort_order',
            'can_use_base_features',
            'can_create_ai_recipes',
            'can_have_common_space',
        ]
        read_only_fields = fields
