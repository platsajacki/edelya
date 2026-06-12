from dataclasses import dataclass

from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.marketing.models.model_enums import MessageTemplateName
from apps.marketing.services.sender import NotificationSender, fmt_date
from apps.subscriptions.api.serializers.subscriptions import SubscriptionSerializer
from apps.subscriptions.api.services.base import CurrentSubscriptionService
from apps.subscriptions.models.model_enums import SubscriptionStatus
from apps.users.models.consents import ConsentLog
from apps.users.models.model_enums import ConsentAction, ConsentType
from core.logging_handlers import loki_logger
from core.utils import get_client_ip


@dataclass
class SubscriptionResumer(CurrentSubscriptionService):
    serializer_class: type[SubscriptionSerializer]

    def _validate_resuming(self) -> None:
        if self.subscription.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL):
            raise ValidationError('Subscription cannot be resumed in current status.')

    def get_validators(self) -> list:
        return super().get_validators() + [self._validate_resuming]

    def _log_granted_recurring_payments(self) -> None:
        try:
            ConsentLog.objects.create(
                user=self.authenticated_user,
                consent_type=ConsentType.RECURRING_PAYMENTS,
                action=ConsentAction.GRANTED,
                metadata={'action': 'resume_subscription'},
                ip_address=get_client_ip(self.request),
                user_agent=self.request.headers.get('User-Agent'),
            )
        except Exception:
            loki_logger.error(
                f'Failed to create consent log for user {self.authenticated_user.id} on resume_subscription',
                exc_info=True,
            )

    @transaction.atomic
    def act(self) -> Response:
        self.subscription.auto_renew = True
        self.subscription.cancelled_at = None
        self.subscription.save(update_fields=['auto_renew', 'cancelled_at'])
        self._log_granted_recurring_payments()
        NotificationSender(
            self.authenticated_user,
            MessageTemplateName.SUBSCRIPTION_AUTO_RENEW_RESUMED,
            {
                'tariff_name': self.subscription.tariff.name,
                'period_end': fmt_date(self.subscription.current_period_end),
            },
        )()
        serializer = self.serializer_class(self.subscription)
        return Response(serializer.data)
