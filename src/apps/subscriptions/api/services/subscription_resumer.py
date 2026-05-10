from dataclasses import dataclass
from dataclasses import field as dc_field

from django.db import transaction
from rest_framework.exceptions import AuthenticationFailed, NotFound, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from apps.subscriptions.api.serializers.subscriptions import SubscriptionSerializer
from apps.subscriptions.models import Subscription
from apps.subscriptions.models.model_enums import SubscriptionStatus
from apps.users.models import User
from apps.users.models.consents import ConsentLog
from apps.users.models.model_enums import ConsentAction, ConsentType
from core.base.services import BaseService
from core.logging_handlers import loki_logger
from core.utils import get_client_ip


@dataclass
class SubscriptionResumer(BaseService):
    request: Request
    serializer_class: type[SubscriptionSerializer]
    authenticated_user: User = dc_field(init=False)
    subscription: Subscription = dc_field(init=False)

    def _validate_user(self) -> None:
        if not isinstance(self.request.user, User):
            raise AuthenticationFailed('User must be authenticated.')
        self.authenticated_user = self.request.user

    def _validate_subscription(self) -> None:
        try:
            self.subscription = Subscription.objects.with_tariff().get(user=self.authenticated_user)
        except Subscription.DoesNotExist as e:
            raise NotFound('No subscription found.') from e
        if self.subscription.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL):
            raise ValidationError('Subscription cannot be resumed in current status.')

    def get_validators(self) -> list:
        return super().get_validators() + [self._validate_user, self._validate_subscription]

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
        serializer = self.serializer_class(self.subscription)
        return Response(serializer.data)
