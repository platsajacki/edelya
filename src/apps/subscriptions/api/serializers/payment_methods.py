from rest_framework.serializers import ModelSerializer

from apps.subscriptions.models import PaymentMethod


class PaymentMethodSerializer(ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = [
            'id',
            'card_type',
            'card_last4',
            'title',
            'is_active',
        ]
        read_only_fields = fields
