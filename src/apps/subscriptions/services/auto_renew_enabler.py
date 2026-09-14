from dataclasses import dataclass

from apps.marketing.models.model_enums import MessageTemplateName
from apps.marketing.services.sender import NotificationSender, fmt_date
from apps.subscriptions.models import Subscription
from core.base.services import BaseService


@dataclass
class AutoRenewEnabler(BaseService):
    subscription: Subscription

    def act(self) -> None:
        self.subscription.enable_auto_renew()
        NotificationSender(
            self.subscription.user,
            MessageTemplateName.SUBSCRIPTION_AUTO_RENEW_RESUMED,
            {
                'tariff_name': self.subscription.tariff.name,
                'period_end': fmt_date(self.subscription.current_period_end),
            },
        )()
