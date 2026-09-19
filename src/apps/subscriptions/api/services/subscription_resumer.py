from dataclasses import dataclass

from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.subscriptions.api.serializers.subscriptions import SubscriptionSerializer
from apps.subscriptions.api.services.base import CurrentSubscriptionService
from apps.subscriptions.api.services.payment_method_binder import PaymentMethodBinder
from apps.subscriptions.services.auto_renew_enabler import AutoRenewEnabler
from apps.subscriptions.services.webhook_handler import WebhookAction
from apps.users.models.consents import ConsentLog
from apps.users.models.model_enums import ConsentAction, ConsentType
from core.logging_handlers import app_logger
from core.utils import get_client_ip


@dataclass
class SubscriptionResumer(CurrentSubscriptionService):
    serializer_class: type[SubscriptionSerializer]

    def _validate_resuming(self) -> None:
        if not self.subscription.is_resumable:
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
            app_logger.error(
                f'Failed to create consent log for user {self.authenticated_user.id} on resume_subscription',
                exc_info=True,
            )

    def _start_card_binding(self) -> Response:
        binder = PaymentMethodBinder(user=self.authenticated_user, action=WebhookAction.RESUME_CARD_BINDING)
        return Response(binder())

    @transaction.atomic
    def act(self) -> Response:
        self._log_granted_recurring_payments()
        if self.subscription.payment_method is None:
            return self._start_card_binding()
        AutoRenewEnabler(self.subscription)()
        serializer = self.serializer_class(self.subscription)
        return Response(serializer.data)
