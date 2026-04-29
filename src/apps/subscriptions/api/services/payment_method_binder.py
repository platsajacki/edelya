from dataclasses import dataclass
from dataclasses import field as dc_field
from uuid import uuid4

from django.db import transaction

from apps.subscriptions.api.services.tariff_selector import RedirectContext, RedirectResponse, ResponseAction
from apps.subscriptions.models import PaymentMethod
from apps.subscriptions.models.model_enums import PaymentStatus, PaymentType
from apps.subscriptions.models.payments import Payment
from apps.subscriptions.services.yookassa_payments import yookassa_service
from apps.users.models import User
from core.base.exceptions import ConflictError
from core.base.services import BaseService


@dataclass
class PaymentMethodBinder(BaseService):
    user: User
    idempotence_key: str = dc_field(default_factory=lambda: str(uuid4()))

    def validate(self) -> None:
        if PaymentMethod.objects.filter(user=self.user).exists():
            raise ConflictError('Payment method already exists. Delete the existing one before adding a new one.')

    @transaction.atomic
    def act(self) -> RedirectResponse:
        yookassa_payment = yookassa_service.create_payment_method_binding(idempotence_key=self.idempotence_key)
        Payment.objects.create(
            subscription=self.user.subscription,
            user=self.user,
            amount=0,
            payment_type=PaymentType.ZERO_AMOUNT_BINDING,
            status=PaymentStatus.PENDING,
            idempotence_key=self.idempotence_key,
            yookassa_payment_id=yookassa_payment.id,
            metadata={},
        )
        return RedirectResponse(
            action=ResponseAction.REDIRECT.value,
            confirmation_url=yookassa_payment.confirmation.confirmation_url,
            context=RedirectContext.CARD_BINDING.value,
            description='Please complete card binding via the confirmation URL.',
        )
