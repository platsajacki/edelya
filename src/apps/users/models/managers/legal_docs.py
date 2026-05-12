from typing import TYPE_CHECKING

from core.base.managers import BaseManager, BaseQuerySet

if TYPE_CHECKING:
    from apps.users.models.legal_docs import PrivacyPolicyVersion, TermsOfServiceVersion  # noqa: F401


class TermsOfServiceVersionQuerySet(BaseQuerySet['TermsOfServiceVersion']):
    def active(self) -> TermsOfServiceVersionQuerySet:
        return self.filter(is_active=True)

    def latest_first(self) -> TermsOfServiceVersionQuerySet:
        return self.order_by('-published_at')


class TermsOfServiceVersionManager(BaseManager['TermsOfServiceVersion', TermsOfServiceVersionQuerySet]):
    def get_queryset_class(self) -> type[TermsOfServiceVersionQuerySet]:
        return TermsOfServiceVersionQuerySet

    def active(self) -> TermsOfServiceVersionQuerySet:
        return self.get_queryset().active()

    def latest_first(self) -> TermsOfServiceVersionQuerySet:
        return self.get_queryset().active().latest_first()

    def current(self) -> TermsOfServiceVersion | None:
        return self.latest_first().first()


class PrivacyPolicyVersionQuerySet(BaseQuerySet['PrivacyPolicyVersion']):
    def active(self) -> PrivacyPolicyVersionQuerySet:
        return self.filter(is_active=True)

    def latest_first(self) -> PrivacyPolicyVersionQuerySet:
        return self.order_by('-published_at')


class PrivacyPolicyVersionManager(BaseManager['PrivacyPolicyVersion', PrivacyPolicyVersionQuerySet]):
    def get_queryset_class(self) -> type[PrivacyPolicyVersionQuerySet]:
        return PrivacyPolicyVersionQuerySet

    def active(self) -> PrivacyPolicyVersionQuerySet:
        return self.get_queryset().active()

    def latest_first(self) -> PrivacyPolicyVersionQuerySet:
        return self.get_queryset().active().latest_first()

    def current(self) -> PrivacyPolicyVersion | None:
        return self.latest_first().first()
