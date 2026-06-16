from pytest_mock import MockFixture, MockType

from decimal import Decimal
from uuid import uuid4

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIClient

from apps.subscriptions.api.serializers.subscriptions import SubscriptionSerializer
from apps.subscriptions.api.services.subscription_retry_payment_starter import SubscriptionRetryPaymentStarter
from apps.subscriptions.models import Subscription, Tariff
from apps.subscriptions.models.model_enums import PaymentStatus, PaymentType, SubscriptionStatus
from apps.subscriptions.models.payments import Payment
from apps.subscriptions.services.webhook_handler import WebhookAction
from apps.users.models import User

RETRY_PAYMENT_URL = reverse('api_v1:subscriptions:subscriptions:subscription-retry-payment')


class TestSubscriptionRetryPaymentViewSet:
    def test_anon_user_gets_401(self, api_client: APIClient) -> None:
        response = api_client.post(RETRY_PAYMENT_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_without_subscription_gets_404(self, api_client: APIClient, telegram_user: User) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(RETRY_PAYMENT_URL)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_not_expired_subscription_gets_400(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(RETRY_PAYMENT_URL)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_no_active_payment_method_gets_409(
        self,
        api_client: APIClient,
        telegram_user: User,
        expired_subscription_with_payment_method: Subscription,
    ) -> None:
        assert expired_subscription_with_payment_method.payment_method is not None
        expired_subscription_with_payment_method.payment_method.is_active = False
        expired_subscription_with_payment_method.payment_method.save(update_fields=['is_active'])
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(RETRY_PAYMENT_URL)
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_pending_recurring_payment_gets_409(
        self,
        api_client: APIClient,
        telegram_user: User,
        expired_subscription_with_payment_method: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        Payment.objects.create(
            subscription=expired_subscription_with_payment_method,
            user=telegram_user,
            amount=paid_tariff.price,
            payment_type=PaymentType.RECURRING,
            status=PaymentStatus.PENDING,
            idempotence_key=uuid4(),
            metadata={'action': WebhookAction.RECURRING},
        )
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(RETRY_PAYMENT_URL)
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_yookassa_succeeded_returns_200_and_activates_subscription(
        self,
        api_client: APIClient,
        telegram_user: User,
        expired_subscription_with_payment_method: Subscription,
        mock_yookassa_payment_create: MockType,
        yookassa_succeeded_response: MockType,
    ) -> None:
        mock_yookassa_payment_create.return_value = yookassa_succeeded_response
        before = timezone.now()
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(RETRY_PAYMENT_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['action'] == 'success'
        assert response.data['payment_status'] == PaymentStatus.SUCCEEDED
        expired_subscription_with_payment_method.refresh_from_db()
        assert expired_subscription_with_payment_method
        assert expired_subscription_with_payment_method.status == SubscriptionStatus.ACTIVE
        assert expired_subscription_with_payment_method.current_period_start
        assert expired_subscription_with_payment_method.current_period_start >= before
        assert expired_subscription_with_payment_method.current_period_end
        assert expired_subscription_with_payment_method.current_period_end == (
            expired_subscription_with_payment_method.tariff.get_next_period_end(
                expired_subscription_with_payment_method.current_period_start
            )
        )

    def test_yookassa_canceled_returns_402_and_keeps_subscription_expired(
        self,
        api_client: APIClient,
        telegram_user: User,
        expired_subscription_with_payment_method: Subscription,
        mock_yookassa_payment_create: MockType,
        yookassa_canceled_response: MockType,
    ) -> None:
        mock_yookassa_payment_create.return_value = yookassa_canceled_response
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(RETRY_PAYMENT_URL)
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert response.data['action'] == 'payment_failed'
        assert response.data['payment_status'] == PaymentStatus.CANCELED
        expired_subscription_with_payment_method.refresh_from_db()
        assert expired_subscription_with_payment_method.status == SubscriptionStatus.EXPIRED
        payment = Payment.objects.filter(
            subscription=expired_subscription_with_payment_method,
            payment_type=PaymentType.SINGLE_PAYMENT,
        ).latest('created_at')
        assert payment.status == PaymentStatus.CANCELED
        assert payment.cancellation_reason == 'card_expired'


class TestSubscriptionRetryPaymentStarter:
    def test_creates_payment_with_correct_fields(
        self,
        retry_payment_request: Request,
        expired_subscription_with_payment_method: Subscription,
    ) -> None:
        service = SubscriptionRetryPaymentStarter(
            request=retry_payment_request,
            serializer_class=SubscriptionSerializer,
        )
        service.validate()
        payment = service._create_payment()
        assert payment.subscription == expired_subscription_with_payment_method
        assert payment.user == expired_subscription_with_payment_method.user
        assert payment.amount == Decimal(str(expired_subscription_with_payment_method.tariff.price))
        assert payment.payment_type == PaymentType.SINGLE_PAYMENT
        assert payment.status == PaymentStatus.PENDING
        assert payment.payment_method == expired_subscription_with_payment_method.payment_method
        assert payment.metadata['action'] == WebhookAction.RETRY_PAYMENT

    def test_calls_yookassa_with_saved_payment_method(
        self,
        mocker: MockFixture,
        retry_payment_request: Request,
        expired_subscription_with_payment_method: Subscription,
        yookassa_succeeded_response: MockType,
    ) -> None:
        mock_create_payment = mocker.patch(
            'apps.subscriptions.api.services.subscription_retry_payment_starter.yookassa_service.create_payment',
            return_value=yookassa_succeeded_response,
        )
        service = SubscriptionRetryPaymentStarter(
            request=retry_payment_request,
            serializer_class=SubscriptionSerializer,
        )
        service.validate()
        payment = service._create_payment()
        service._charge_payment(payment)
        call_kwargs = mock_create_payment.call_args.kwargs
        assert call_kwargs['amount'] == Decimal(str(expired_subscription_with_payment_method.tariff.price))
        assert expired_subscription_with_payment_method.payment_method is not None
        assert call_kwargs['payment_method_id'] == (
            expired_subscription_with_payment_method.payment_method.yookassa_payment_method_id
        )
        assert call_kwargs['capture'] is True
        assert call_kwargs['idempotence_key'] == str(payment.idempotence_key)

    def test_success_starts_new_period_from_now(
        self,
        retry_payment_request: Request,
        expired_subscription_with_payment_method: Subscription,
        mock_yookassa_payment_create: MockType,
        yookassa_succeeded_response: MockType,
    ) -> None:
        old_period_end = expired_subscription_with_payment_method.current_period_end
        mock_yookassa_payment_create.return_value = yookassa_succeeded_response
        service = SubscriptionRetryPaymentStarter(
            request=retry_payment_request,
            serializer_class=SubscriptionSerializer,
        )
        before = timezone.now()
        response = service()
        expired_subscription_with_payment_method.refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert expired_subscription_with_payment_method.current_period_start
        assert expired_subscription_with_payment_method.current_period_end
        assert expired_subscription_with_payment_method.current_period_start >= before
        assert expired_subscription_with_payment_method.current_period_end != old_period_end
