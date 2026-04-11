from typing import TYPE_CHECKING

from core.base.managers import ActiveManager, ActiveQuerySet

if TYPE_CHECKING:
    from apps.subscriptions.models import Tariff  # noqa: F401


class TariffQuerySet(ActiveQuerySet['Tariff']):
    def published(self) -> TariffQuerySet:
        return self.filter(published=True)

    def with_subscriptions(self) -> TariffQuerySet:
        return self.prefetch_related('subscriptions')


class TariffManager(ActiveManager['Tariff', TariffQuerySet]):
    def get_queryset_class(self) -> type[TariffQuerySet]:
        return TariffQuerySet

    def published(self) -> TariffQuerySet:
        return self.get_queryset().published()

    def actived(self) -> TariffQuerySet:
        return self.get_queryset().actived()
