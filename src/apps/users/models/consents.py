from django.db import models

from apps.users.models.legal_docs import PrivacyPolicyVersion, TermsOfServiceVersion
from apps.users.models.model_enums import ConsentAction, ConsentType
from apps.users.models.users import User
from core.base.abstract_models import BaseModel
from core.base.validators import dict_validator


class ConsentLog(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='consent_logs',
        verbose_name='User',
    )
    consent_type = models.CharField(
        'Consent Type',
        max_length=50,
        choices=ConsentType.choices,
        help_text='Type of consent',
    )
    action = models.CharField(
        'Action',
        max_length=10,
        choices=ConsentAction.choices,
        default=ConsentAction.GRANTED.value,
        help_text='Granted or revoked',
    )
    metadata = models.JSONField(
        verbose_name='Metadata',
        blank=True,
        null=True,
        default=dict,
        validators=[dict_validator],
        help_text='Optional structured metadata',
    )
    ip_address = models.GenericIPAddressField(
        'IP Address',
        blank=True,
        null=True,
    )
    user_agent = models.TextField(
        'User Agent',
        blank=True,
        null=True,
    )
    terms_of_service_version = models.ForeignKey(
        TermsOfServiceVersion,
        on_delete=models.SET_NULL,
        related_name='consent_logs',
        verbose_name='Terms of Service Version',
        blank=True,
        null=True,
    )
    privacy_policy_version = models.ForeignKey(
        PrivacyPolicyVersion,
        on_delete=models.SET_NULL,
        related_name='consent_logs',
        verbose_name='Privacy Policy Version',
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'Consent Log'
        verbose_name_plural = 'Consent Logs'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.user_id} {self.consent_type} {self.action}'
