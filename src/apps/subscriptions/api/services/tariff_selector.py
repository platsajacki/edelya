from dataclasses import dataclass
from dataclasses import field as dc_field
from decimal import Decimal
from enum import Enum, StrEnum
from typing import Literal, TypedDict
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotAuthenticated, NotFound
from rest_framework.request import Request
from rest_framework.response import Response

from apps.subscriptions.api.serializers.subscriptions import SubscriptionSerializer
from apps.subscriptions.models import Subscription, Tariff
from apps.subscriptions.models.model_enums import PaymentStatus, PaymentType, SubscriptionStatus
from apps.subscriptions.models.payment_methods import PaymentMethod
from apps.subscriptions.models.payments import Payment
from apps.subscriptions.services.yookassa_payments import yookassa_service
from apps.users.models import User
from core.base.exceptions import ConflictError
from core.base.services import BaseService, BaseViewSetService


class ResponseAction(Enum):
    REDIRECT = 'redirect'
    SUCCESS = 'success'


class ResponseDescription(StrEnum):
    CARD_BINDING = 'Please bind your card to select the tariff.'
    PAYMENT_REQUIRED = 'Please complete payment to activate your subscription.'
    TARIFF_SCHEDULED = 'Tariff change scheduled for the next billing cycle.'
    DOWNGRADE_SCHEDULED = 'Tariff downgrade scheduled for the next billing cycle.'
    UPGRADE_SUCCESS = 'Tariff upgraded successfully.'


class RedirectResponse(TypedDict):
    action: Literal['redirect']
    confirmation_url: str
    context: Literal['card_binding', 'payment', 'upgrade_payment']
    description: str


class RedirectContext(Enum):
    CARD_BINDING = 'card_binding'
    PAYMENT = 'payment'
    UPGRADE_PAYMENT = 'upgrade_payment'


class SuccessResponse(TypedDict):
    action: Literal['success']
    subscription: dict  # Serialized subscription data
    description: str


TariffSelectorResponse = RedirectResponse | SuccessResponse


@dataclass
class TariffService(BaseService):
    user: User
    tariff: Tariff
    idempotence_key: str = dc_field(default_factory=lambda: str(uuid4()))


@dataclass
class TrialTariffBinder(TariffService):
    """TRIAL + no payment_method → zero-amount card binding."""

    def create_pending_payment(self, yookassa_payment_id: str, metadata: dict | None = None) -> Payment:
        return Payment.objects.create(
            subscription=self.user.subscription,
            user=self.user,
            amount=0,
            payment_type=PaymentType.ZERO_AMOUNT_BINDING,
            status=PaymentStatus.PENDING,
            idempotence_key=self.idempotence_key,
            yookassa_payment_id=yookassa_payment_id,
            metadata=metadata or {},
        )

    @transaction.atomic
    def act(self) -> TariffSelectorResponse:
        yookassa_payment = yookassa_service.create_payment_method_binding(idempotence_key=self.idempotence_key)
        confirmation_url = yookassa_payment.confirmation.confirmation_url
        self.create_pending_payment(
            yookassa_payment_id=yookassa_payment.id, metadata={'tariff_id': str(self.tariff.id)}
        )
        return RedirectResponse(
            action=ResponseAction.REDIRECT.value,
            confirmation_url=confirmation_url,
            context=RedirectContext.CARD_BINDING.value,
            description=ResponseDescription.CARD_BINDING,
        )


@dataclass
class TrialTariffScheduler(TariffService):
    """TRIAL + has payment_method → schedule pending_tariff."""

    @transaction.atomic
    def act(self) -> TariffSelectorResponse:
        self.user.subscription.pending_tariff = self.tariff
        self.user.subscription.save(update_fields=['pending_tariff'])
        return SuccessResponse(
            action=ResponseAction.SUCCESS.value,
            subscription=SubscriptionSerializer(self.user.subscription).data,
            description=ResponseDescription.TARIFF_SCHEDULED,
        )


@dataclass
class TariffActivator(TariffService):
    """EXPIRED / CANCELLED → full payment + card binding."""

    def create_pending_payment(self, yookassa_payment_id: str, metadata: dict | None = None) -> Payment:
        return Payment.objects.create(
            subscription=self.user.subscription,
            user=self.user,
            amount=self.tariff.price,
            payment_type=PaymentType.FIRST_PAYMENT,
            status=PaymentStatus.PENDING,
            idempotence_key=self.idempotence_key,
            yookassa_payment_id=yookassa_payment_id,
            metadata=metadata or {},
        )

    @transaction.atomic
    def act(self) -> TariffSelectorResponse:
        yookassa_payment = yookassa_service.create_payment(
            amount=self.tariff.price,
            save_payment_method=True,
            idempotence_key=self.idempotence_key,
        )
        confirmation_url = yookassa_payment.confirmation.confirmation_url
        self.create_pending_payment(
            yookassa_payment_id=yookassa_payment.id, metadata={'tariff_id': str(self.tariff.id)}
        )
        return RedirectResponse(
            action=ResponseAction.REDIRECT.value,
            confirmation_url=confirmation_url,
            context=RedirectContext.PAYMENT.value,
            description=ResponseDescription.PAYMENT_REQUIRED,
        )


@dataclass
class TariffSwitcher(TariffService):
    """
    ACTIVE → switch tariff by two scenarios:
    UPGRADE (new_price > current_price):
    - списать пропорциональную разницу за остаток периода
    - сразу активировать, сбросить billing cycle

    DOWNGRADE (new_price <= current_price):
    - применить со следующего billing cycle через pending_tariff
    - деньги не возвращать
    """

    def _calc_proration(self, subscription: Subscription) -> Decimal:
        if subscription.current_period_start is None or subscription.current_period_end is None:
            return Decimal(0)
        remaining_days = (subscription.current_period_end - timezone.now()).days
        if remaining_days <= 0:
            return Decimal(0)
        total_days = max(1, (subscription.current_period_end - subscription.current_period_start).days)
        new_price = Decimal(str(self.tariff.price))
        current_price = Decimal(str(subscription.tariff.price))
        proration = Decimal(remaining_days) / Decimal(total_days) * (new_price - current_price)
        return proration.quantize(Decimal('0.01'))

    def create_upgrade_payment(self, yookassa_payment_id: str, amount: Decimal, yookassa_status: str) -> Payment:
        return Payment.objects.create(
            subscription=self.user.subscription,
            user=self.user,
            amount=amount,
            payment_type=PaymentType.RECURRING,
            status=PaymentStatus(yookassa_status),
            idempotence_key=self.idempotence_key,
            yookassa_payment_id=yookassa_payment_id,
            metadata={'tariff_id': str(self.tariff.id), 'is_upgrade': True},
        )

    def update_subscription_to_downgrade(self, subscription: Subscription) -> None:
        subscription.pending_tariff = self.tariff
        subscription.save(update_fields=['pending_tariff'])

    def downgrade(self, subscription: Subscription) -> TariffSelectorResponse:
        pending = subscription.pending_tariff
        if pending and pending.id == self.tariff.id:
            raise ConflictError('You have a pending subscription to this tariff')
        self.update_subscription_to_downgrade(subscription)
        return SuccessResponse(
            action=ResponseAction.SUCCESS.value,
            subscription=SubscriptionSerializer(subscription).data,
            description=ResponseDescription.DOWNGRADE_SCHEDULED,
        )

    def update_subscription_to_upgrade(self, subscription: Subscription) -> None:
        now = timezone.now()
        subscription.current_period_start = now
        subscription.current_period_end = self.tariff.get_next_period_end(now)
        subscription.tariff = self.tariff
        subscription.save(update_fields=['current_period_start', 'current_period_end', 'tariff'])

    def upgrade(self, subscription: Subscription, payment_method: PaymentMethod) -> TariffSelectorResponse:
        proration = self._calc_proration(subscription)
        if proration > 0:
            yoo_payment = yookassa_service.create_payment(
                amount=proration,
                payment_method_id=payment_method.yookassa_payment_method_id,
                idempotence_key=self.idempotence_key,
                metadata={'tariff_id': str(self.tariff.id)},
            )
            self.create_upgrade_payment(
                yookassa_payment_id=yoo_payment.id,
                amount=proration,
                yookassa_status=yoo_payment.status,
            )
            if yoo_payment.status == 'canceled':
                raise ConflictError('Upgrade payment was canceled')
        self.update_subscription_to_upgrade(subscription)
        return SuccessResponse(
            action=ResponseAction.SUCCESS.value,
            subscription=SubscriptionSerializer(subscription).data,
            description=ResponseDescription.UPGRADE_SUCCESS,
        )

    def act(self) -> TariffSelectorResponse:
        subscription = self.user.subscription
        if Decimal(str(self.tariff.price)) <= Decimal(str(subscription.tariff.price)):
            return self.downgrade(subscription)
        if subscription.payment_method is None or not subscription.payment_method.is_active:
            raise ConflictError('Active payment method required to upgrade. Please update your payment info.')
        return self.upgrade(subscription, subscription.payment_method)


@dataclass
class TariffSelector(BaseViewSetService):
    request: Request | None = dc_field(default=None)
    user: User = dc_field(init=False)

    def __post_init__(self) -> None:
        if self.request is None:
            raise ValueError('Request cannot be None')
        if not self.request.user.is_authenticated:
            raise NotAuthenticated('User must be authenticated to select a tariff')
        self.user = self.request.user
        if not hasattr(self.user, 'subscription'):
            raise NotFound('User subscription not found')

    def get_tariff(self) -> Tariff:
        tariff = Tariff.objects.actual().filter(is_trial_tariff=False, id=self.validated_data['tariff_id']).first()
        if not tariff:
            raise NotFound('Tariff not found')
        return tariff

    def check_current_subscription(self, tariff: Tariff) -> None:
        if self.user.subscription.tariff_id == tariff.id:
            raise ConflictError('You are already subscribed to this tariff')

    def check_pending_subscription(self, tariff: Tariff) -> None:
        pending = self.user.subscription.pending_tariff
        if pending and pending.id == tariff.id:
            raise ConflictError('You have a pending subscription to this tariff')

    def _get_sub_service(self, subscription: Subscription, tariff: Tariff) -> TariffService:
        status = subscription.status
        if status == SubscriptionStatus.TRIAL:
            self.check_pending_subscription(tariff)
            if subscription.payment_method is not None and subscription.payment_method.is_active:
                return TrialTariffScheduler(user=self.user, tariff=tariff)
            return TrialTariffBinder(user=self.user, tariff=tariff)
        elif status in (SubscriptionStatus.EXPIRED, SubscriptionStatus.CANCELLED):
            return TariffActivator(user=self.user, tariff=tariff)
        elif status == SubscriptionStatus.ACTIVE:
            return TariffSwitcher(user=self.user, tariff=tariff)
        raise ConflictError(f'Cannot select tariff for subscription with status {status!r}')

    def act(self) -> Response:
        tariff = self.get_tariff()
        subscription = self.user.subscription
        self.check_current_subscription(tariff)
        result = self._get_sub_service(subscription, tariff)()
        return Response(result)
