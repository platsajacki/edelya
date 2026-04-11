from typing import TYPE_CHECKING

from core.base.managers import ActiveManager, ActiveQuerySet

if TYPE_CHECKING:
    from apps.subscriptions.models import Tariff  # noqa: F401


class TariffQuerySet(ActiveQuerySet['Tariff']):
    def published(self) -> TariffQuerySet:
        return self.filter(published=True)

    def with_subscriptions(self) -> TariffQuerySet:
        return self.prefetch_related('subscriptions')

    def trial(self) -> TariffQuerySet:
        return self.filter(is_trial_tariff=True)

    def get_trial_tariff(self) -> Tariff:
        return self.trial().actived().get()


class TariffManager(ActiveManager['Tariff', TariffQuerySet]):
    def get_queryset_class(self) -> type[TariffQuerySet]:
        return TariffQuerySet

    def published(self) -> TariffQuerySet:
        return self.get_queryset().published()

    def actived(self) -> TariffQuerySet:
        return self.get_queryset().actived()

    def get_trial_tariff(self) -> Tariff:
        return self.get_queryset().get_trial_tariff()

    def trial_duration(self) -> int:
        trial_tariff = self.get_trial_tariff()
        return trial_tariff.trial_days
