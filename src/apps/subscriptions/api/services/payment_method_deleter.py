from dataclasses import dataclass

from django.db import transaction
from rest_framework.request import Request

from apps.marketing.models.model_enums import MessageTemplateName
from apps.marketing.services.sender import NotificationSender
from apps.subscriptions.models import Subscription
from apps.users.models.consents import ConsentLog
from apps.users.models.model_enums import ConsentAction, ConsentType
from core.base.services import BaseInstanceService
from core.logging_handlers import loki_logger
from core.utils import get_client_ip


@dataclass
class PaymentMethodDeleter(BaseInstanceService):
    request: Request

    def create_log(self) -> None:
        try:
            ConsentLog.objects.create(
                user=self.request.user,
                consent_type=ConsentType.PAYMENT_METHOD_STORAGE,
                action=ConsentAction.REVOKED,
                metadata={'action': 'delete_payment_method'},
                ip_address=get_client_ip(self.request),
                user_agent=self.request.headers.get('User-Agent'),
            )
        except Exception:
            loki_logger.error(
                self.get_log_msg(
                    f'Failed to create consent log for user {self.request.user.id} on delete_payment_method'
                ),
                exc_info=True,
            )

    @transaction.atomic
    def delete_payment_method(self) -> None:
        subscription = Subscription.objects.select_for_update().filter(user=self.request.user).first()
        if subscription is not None and subscription.auto_renew:
            subscription.disable_auto_renew()
        self.instance.delete()

    def act(self) -> None:
        self.create_log()
        card_name = getattr(self.instance, 'card_name', 'Your card')
        self.delete_payment_method()
        NotificationSender(self.request.user, MessageTemplateName.SUBSCRIPTION_CARD_UNBOUND, {'card_name': card_name})()
