from rest_framework import serializers

from apps.users.models.legal_docs import PrivacyPolicyVersion, TermsOfServiceVersion


class TermsOfServiceVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsOfServiceVersion
        fields = ['id', 'version', 'content', 'published_at', 'is_active']


class PrivacyPolicyVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacyPolicyVersion
        fields = ['id', 'version', 'content', 'published_at', 'is_active']
