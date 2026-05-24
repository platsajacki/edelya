from apps.users.models.managers.legal_docs import (
    PrivacyPolicyVersionManager,
    PrivacyPolicyVersionQuerySet,
    TermsOfServiceVersionManager,
    TermsOfServiceVersionQuerySet,
)

__all__ = [
    'TermsOfServiceVersionQuerySet',
    'TermsOfServiceVersionManager',
    'PrivacyPolicyVersionQuerySet',
    'PrivacyPolicyVersionManager',
]
