from django.db import models
from django.utils import timezone

from apps.users.models.managers.legal_docs import (
    PrivacyPolicyVersionManager,
    TermsOfServiceVersionManager,
)
from core.base.abstract_models import BaseModel


class LegalDocumentVersion(BaseModel):
    version = models.CharField(
        verbose_name='Version',
        max_length=50,
        help_text='Human-readable version label, e.g. "1.0", "2026-05-12"',
    )
    content = models.TextField(
        verbose_name='Content',
        help_text='Full text of the document shown to the user',
    )
    published_at = models.DateTimeField(
        verbose_name='Published At',
        default=timezone.now,
    )
    is_active = models.BooleanField(
        verbose_name='Is Active',
        default=True,
        help_text='Only active versions are shown to users',
    )

    class Meta:
        abstract = True
        ordering = ['-published_at']

    def __str__(self) -> str:
        return f'{self.version} ({self.published_at:%Y-%m-%d})'


class TermsOfServiceVersion(LegalDocumentVersion):
    objects: TermsOfServiceVersionManager = TermsOfServiceVersionManager()  # type: ignore[misc]

    class Meta(LegalDocumentVersion.Meta):
        verbose_name = 'Terms of Service Version'
        verbose_name_plural = 'Terms of Service Versions'


class PrivacyPolicyVersion(LegalDocumentVersion):
    objects: PrivacyPolicyVersionManager = PrivacyPolicyVersionManager()  # type: ignore[misc]

    class Meta(LegalDocumentVersion.Meta):
        verbose_name = 'Privacy Policy Version'
        verbose_name_plural = 'Privacy Policy Versions'
