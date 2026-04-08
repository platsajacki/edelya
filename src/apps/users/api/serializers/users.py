from rest_framework import serializers

from apps.users.models.users import User


class OnboardingDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['onboarding_data']

    def validate_onboarding_data(self, value: dict) -> dict:
        if not isinstance(value, dict):
            raise serializers.ValidationError('onboarding_data must be an object/dictionary.')
        for k, v in value.items():
            if not isinstance(k, str):
                raise serializers.ValidationError('All onboarding_data keys must be strings.')
            if not isinstance(v, bool):
                raise serializers.ValidationError('All onboarding_data values must be boolean (true/false).')
        if getattr(self, 'instance', None) is not None:
            prev = self.instance.onboarding_data or {}
            removed = set(prev.keys()) - set(value.keys())
            if removed:
                removed_list = ', '.join(sorted(removed))
                raise serializers.ValidationError(f'Cannot remove keys from onboarding_data: {removed_list}')
        return value
