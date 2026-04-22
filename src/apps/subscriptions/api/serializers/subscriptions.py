from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from apps.subscriptions.api.serializers.tariffs import TariffSerializer
from apps.subscriptions.models import Subscription


class SubscriptionSerializer(ModelSerializer):
    tariff = TariffSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            'id',
            'status',
            'tariff',
            'trial_started_at',
            'days_in_trial',
            'trial_ended_at',
            'current_period_start',
            'current_period_end',
            'auto_renew',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class SubscriptionTariffSelectSerializer(ModelSerializer):
    tariff_id = serializers.UUIDField()

    class Meta:
        model = Subscription
        fields = ['tariff_id']
