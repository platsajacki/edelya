from dataclasses import dataclass

from apps.dishes.models import DishAIDraft
from apps.subscriptions.constants import AI_RECIPE_LIMIT_PER_PERIOD
from apps.subscriptions.models import Subscription
from core.base.services import BaseService


@dataclass(frozen=True)
class AIDraftUsage:
    used: int
    limit: int
    remaining: int

    def to_dict(self) -> dict[str, int]:
        return {
            'used': self.used,
            'limit': self.limit,
            'remaining': self.remaining,
        }


@dataclass
class AIDraftUsageCalculator(BaseService[AIDraftUsage]):
    subscription: Subscription

    def act(self) -> AIDraftUsage:
        used = DishAIDraft.objects.count_by_subscription_period(self.subscription)
        if used < 0:
            return AIDraftUsage(used=0, limit=AI_RECIPE_LIMIT_PER_PERIOD, remaining=0)
        return AIDraftUsage(
            used=used,
            limit=AI_RECIPE_LIMIT_PER_PERIOD,
            remaining=max(AI_RECIPE_LIMIT_PER_PERIOD - used, 0),
        )
