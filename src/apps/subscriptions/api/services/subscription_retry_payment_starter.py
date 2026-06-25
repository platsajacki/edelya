from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal, TypedDict
from uuid import uuid4

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from yookassa.payment import PaymentResponse

from apps.marketing.models.model_enums import MessageTemplateName
from apps.marketing.services.sender import NotificationSender, fmt_date
from apps.subscriptions.api.serializers.subscriptions import SubscriptionSerializer
from apps.subscriptions.api.services.base import CurrentSubscriptionService
from apps.subscriptions.models import Payment, Subscription
from apps.subscriptions.models.model_enums import PaymentStatus, PaymentType, SubscriptionStatus
from apps.subscriptions.models.payment_methods import PaymentMethod
from apps.subscriptions.services.sync_controler import payment_sync_flag_controler
from apps.subscriptions.services.tax_check import TaxCheckSender
from apps.subscriptions.services.webhook_handler import WebhookAction
from apps.subscriptions.services.yookassa_payments import yookassa_service
from core.base.exceptions import ConflictError


class RetryPaymentAction(StrEnum):
    SUCCESS = 'success'
    PAYMENT_FAILED = 'payment_failed'


class RetryPaymentDescription(StrEnum):
    SUCCEEDED = 'Subscription payment completed successfully.'
    FAILED = 'Subscription payment failed.'


class RetryPaymentResponse(TypedDict):
    action: Literal['success', 'payment_failed']
    payment_status: Literal['succeeded', 'canceled']
    subscription: dict
    description: str


@dataclass
class SubscriptionRetryPaymentStarter(CurrentSubscriptionService):
    serializer_class: type[SubscriptionSerializer]

    def get_subscription_queryset(self) -> QuerySet[Subscription]:
        return super().get_subscription_queryset().select_related('payment_method')

    def _validate_status(self) -> None:
        if self.subscription.status != SubscriptionStatus.EXPIRED:
            raise ValidationError('Subscription payment retry is available only for expired subscriptions.')

    def _validate_payment_method(self) -> None:
        if self.subscription.payment_method is None or not self.subscription.payment_method.is_active:
            raise ConflictError('Active payment method is required to retry subscription payment.')

    def _validate_no_pending_recurring_payment(self) -> None:
        if Payment.objects.has_pending_recurring_payment(self.subscription):
            raise ConflictError('Subscription has a pending recurring payment.')

    def get_validators(self) -> list:
        return super().get_validators() + [
            self._validate_status,
            self._validate_payment_method,
            self._validate_no_pending_recurring_payment,
        ]

    def _get_payment_method(self) -> PaymentMethod:
        if self.subscription.payment_method is None or not self.subscription.payment_method.is_active:
            raise ConflictError('Active payment method is required to retry subscription payment.')
        return self.subscription.payment_method

    def _create_payment(self) -> Payment:
        idempotence_key = str(uuid4())
        return Payment.objects.create(
            subscription=self.subscription,
            user=self.authenticated_user,
            amount=self.subscription.tariff.price,
            payment_type=PaymentType.SINGLE_PAYMENT,
            status=PaymentStatus.PENDING,
            idempotence_key=idempotence_key,
            payment_method=self.subscription.payment_method,
            metadata={
                'action': WebhookAction.RETRY_PAYMENT,
                'tariff_id': str(self.subscription.tariff_id),
                'idempotence_key': idempotence_key,
            },
        )

    def _charge_payment(self, payment: Payment) -> PaymentResponse:
        payment_method = self._get_payment_method()
        payment_sync_flag_controler.set_payment_sync_flag(str(payment.idempotence_key))
        yoo_response = yookassa_service.create_payment(
            amount=payment.amount,
            payment_method_id=payment_method.yookassa_payment_method_id,
            capture=True,
            idempotence_key=str(payment.idempotence_key),
            description=f'Разовая оплата подписки "{self.subscription.tariff.name}"',
            metadata=payment.metadata,
        )
        payment.yookassa_payment_id = yoo_response.id
        payment.save(update_fields=['yookassa_payment_id'])
        return yoo_response

    def _serialize_response(self, action: RetryPaymentAction, payment_status: PaymentStatus) -> RetryPaymentResponse:
        description = (
            RetryPaymentDescription.SUCCEEDED
            if payment_status == PaymentStatus.SUCCEEDED
            else RetryPaymentDescription.FAILED
        )
        return RetryPaymentResponse(
            action=action.value,
            payment_status=payment_status.value,  # type: ignore[typeddict-item]
            subscription=self.serializer_class(self.subscription).data,
            description=description,
        )

    def _send_notification_for_successful_payment(self, payment: Payment) -> None:
        NotificationSender(
            self.authenticated_user,
            MessageTemplateName.SUBSCRIPTION_RECURRING_PAYMENT_SUCCEEDED,
            {
                'tariff_name': self.subscription.tariff.name,
                'amount': str(payment.amount),
                'currency': str(payment.currency),
                'period_end': fmt_date(self.subscription.current_period_end),
            },
        )()

    def _send_notification_for_failed_payment(self, payment: Payment) -> None:
        NotificationSender(
            self.authenticated_user,
            MessageTemplateName.SUBSCRIPTION_PAYMENT_FAILED,
            {
                'tariff_name': self.subscription.tariff.name,
                'amount': str(payment.amount),
                'currency': str(payment.currency),
            },
        )()

    def _mark_payment_succeeded(self, payment: Payment, paid_at: datetime) -> None:
        payment.status = PaymentStatus.SUCCEEDED
        payment.paid_at = paid_at
        payment.save(update_fields=['status', 'paid_at'])

    def _activate_subscription(self, period_start: datetime) -> None:
        self.subscription.status = SubscriptionStatus.ACTIVE
        self.subscription.auto_renew = True
        self.subscription.cancelled_at = None
        self.subscription.current_period_start = period_start
        self.subscription.current_period_end = self.subscription.tariff.get_next_period_end(period_start)
        self.subscription.pending_tariff = None
        self.subscription.save(
            update_fields=[
                'status',
                'auto_renew',
                'cancelled_at',
                'current_period_start',
                'current_period_end',
                'pending_tariff',
            ]
        )

    @transaction.atomic
    def _process_successful_payment(self, payment: Payment) -> RetryPaymentResponse:
        now = timezone.now()
        self._mark_payment_succeeded(payment, paid_at=now)
        self._activate_subscription(period_start=now)
        self._send_notification_for_successful_payment(payment)
        TaxCheckSender(payment, f'Разовая оплата подписки на сервис Edelya — {self.subscription.tariff.name}')()
        return self._serialize_response(RetryPaymentAction.SUCCESS, PaymentStatus.SUCCEEDED)

    @transaction.atomic
    def _process_failed_payment(self, payment: Payment, cancellation_reason: str | None) -> RetryPaymentResponse:
        payment.status = PaymentStatus.CANCELED
        payment.cancellation_reason = cancellation_reason or 'Unknown reason'
        payment.save(update_fields=['status', 'cancellation_reason'])
        self._send_notification_for_failed_payment(payment)
        return self._serialize_response(RetryPaymentAction.PAYMENT_FAILED, PaymentStatus.CANCELED)

    def act(self) -> Response:
        payment = self._create_payment()
        yoo_response = self._charge_payment(payment)
        if PaymentStatus(yoo_response.status) == PaymentStatus.SUCCEEDED:
            return Response(self._process_successful_payment(payment))
        cancellation_details = getattr(yoo_response, 'cancellation_details', None)
        reason = getattr(cancellation_details, 'reason', '') or 'Unknown reason'
        return Response(
            self._process_failed_payment(payment, reason),
            status=status.HTTP_402_PAYMENT_REQUIRED,
        )
