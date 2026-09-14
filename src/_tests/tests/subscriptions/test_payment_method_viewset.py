from pytest_mock import MockType

from datetime import timedelta
from unittest.mock import MagicMock

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.marketing.models import Notification
from apps.marketing.models.model_enums import MessageTemplateName
from apps.subscriptions.models import PaymentMethod, Subscription
from apps.subscriptions.models.model_enums import PaymentStatus, PaymentType, SubscriptionStatus
from apps.subscriptions.models.payments import Payment
from apps.subscriptions.tasks.renewals import ChargeRenewalService
from apps.users.models import ConsentLog, User
from apps.users.models.model_enums import ConsentAction, ConsentType

PAYMENT_METHOD_URL = reverse('api_v1:subscriptions:payment-method')


class TestPaymentMethodCreate:
    def test_anon_user_gets_401(self, api_client: APIClient) -> None:
        response = api_client.post(PAYMENT_METHOD_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_user_gets_200(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
        mock_yookassa_payment_method_create: MockType,
    ) -> None:
        mock_yookassa_payment_method_create.return_value.id = 'yoo-pm-new-001'
        mock_yookassa_payment_method_create.return_value.confirmation.confirmation_url = 'https://yookassa.ru/pay'
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(PAYMENT_METHOD_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_response_is_redirect_with_card_binding_context(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
        mock_yookassa_payment_method_create: MockType,
    ) -> None:
        mock_yookassa_payment_method_create.return_value.id = 'yoo-pm-new-002'
        mock_yookassa_payment_method_create.return_value.confirmation.confirmation_url = 'https://yookassa.ru/pay'
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(PAYMENT_METHOD_URL)
        assert response.data['action'] == 'redirect'
        assert response.data['context'] == 'card_binding'
        assert response.data['confirmation_url'] == 'https://yookassa.ru/pay'

    def test_user_with_existing_payment_method_gets_409(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_payment_method: PaymentMethod,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(PAYMENT_METHOD_URL)
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_yookassa_not_called_when_method_exists(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_payment_method: PaymentMethod,
        mock_yookassa_payment_method_create: MockType,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        api_client.post(PAYMENT_METHOD_URL)
        mock_yookassa_payment_method_create.assert_not_called()

    def test_yookassa_service_is_called(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
        mock_yookassa_payment_method_create: MockType,
    ) -> None:
        mock_yookassa_payment_method_create.return_value.id = 'yoo-pm-new-003'
        mock_yookassa_payment_method_create.return_value.confirmation.confirmation_url = 'https://yookassa.ru/pay'
        api_client.force_authenticate(user=telegram_user)
        api_client.post(PAYMENT_METHOD_URL)
        mock_yookassa_payment_method_create.assert_called_once()

    def test_creates_zero_amount_binding_payment_record(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
        mock_yookassa_payment_method_create: MockType,
    ) -> None:
        """PaymentMethodBinder creates a Payment(ZERO_AMOUNT_BINDING) linked to user's subscription."""
        fake_pm = MagicMock()
        fake_pm.id = 'yoo-pm-binding-abc'
        fake_pm.confirmation.confirmation_url = 'https://yookassa.ru/pay'
        mock_yookassa_payment_method_create.return_value = fake_pm
        api_client.force_authenticate(user=telegram_user)
        api_client.post(PAYMENT_METHOD_URL)
        payment = Payment.objects.get(yookassa_payment_id='yoo-pm-binding-abc')
        assert payment.subscription == trial_subscription
        assert payment.user == telegram_user
        assert payment.amount == 0
        assert payment.payment_type == PaymentType.ZERO_AMOUNT_BINDING
        assert payment.status == PaymentStatus.PENDING
        assert payment.metadata == {'action': 'card_binding', 'idempotence_key': str(payment.idempotence_key)}


class TestPaymentMethodRetrieve:
    def test_anon_user_gets_401(self, api_client: APIClient) -> None:
        response = api_client.get(PAYMENT_METHOD_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_owner_gets_200(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_payment_method: PaymentMethod,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(PAYMENT_METHOD_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_response_contains_expected_fields(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_payment_method: PaymentMethod,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(PAYMENT_METHOD_URL)
        assert response.data['id'] == str(active_payment_method.id)
        assert response.data['card_last4'] == active_payment_method.card_last4
        assert response.data['card_type'] == active_payment_method.card_type
        assert response.data['is_active'] == active_payment_method.is_active

    def test_user_without_payment_method_gets_404(
        self,
        api_client: APIClient,
        telegram_user: User,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(PAYMENT_METHOD_URL)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_another_user_cannot_see_others_method(
        self,
        api_client: APIClient,
        another_telegram_user: User,
        active_payment_method: PaymentMethod,
    ) -> None:
        api_client.force_authenticate(user=another_telegram_user)
        response = api_client.get(PAYMENT_METHOD_URL)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestPaymentMethodDestroy:
    def test_anon_user_gets_401(self, api_client: APIClient) -> None:
        response = api_client.delete(PAYMENT_METHOD_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_owner_gets_204(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_payment_method: PaymentMethod,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.delete(PAYMENT_METHOD_URL)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_payment_method_is_deleted(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_payment_method: PaymentMethod,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        api_client.delete(PAYMENT_METHOD_URL)
        assert not PaymentMethod.objects.filter(id=active_payment_method.id).exists()

    def test_user_without_payment_method_gets_404(
        self,
        api_client: APIClient,
        telegram_user: User,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.delete(PAYMENT_METHOD_URL)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_another_user_cannot_delete_others_method(
        self,
        api_client: APIClient,
        another_telegram_user: User,
        active_payment_method: PaymentMethod,
    ) -> None:
        api_client.force_authenticate(user=another_telegram_user)
        response = api_client.delete(PAYMENT_METHOD_URL)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_creates_revoked_payment_method_storage_log(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_payment_method: PaymentMethod,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        api_client.delete(PAYMENT_METHOD_URL)
        assert ConsentLog.objects.filter(
            user=telegram_user,
            consent_type=ConsentType.PAYMENT_METHOD_STORAGE,
            action=ConsentAction.REVOKED,
        ).exists()

    def test_delete_sends_card_unbound_notification(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_payment_method: PaymentMethod,
    ) -> None:
        """Отвязка карты отправляет уведомление CARD_UNBOUND."""
        api_client.force_authenticate(user=telegram_user)
        api_client.delete(PAYMENT_METHOD_URL)
        assert Notification.objects.filter(
            user=telegram_user,
            template__name=MessageTemplateName.SUBSCRIPTION_CARD_UNBOUND,
            delivered=True,
        ).exists()

    def test_delete_disables_auto_renew(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
    ) -> None:
        """Удаление карты отключает автопродление, как обещано в интерфейсе."""
        api_client.force_authenticate(user=telegram_user)
        api_client.delete(PAYMENT_METHOD_URL)
        active_subscription_with_period.refresh_from_db()
        assert active_subscription_with_period.auto_renew is False
        assert active_subscription_with_period.cancelled_at is not None
        assert active_subscription_with_period.payment_method is None
        assert active_subscription_with_period.status == SubscriptionStatus.ACTIVE

    def test_delete_creates_revoked_recurring_payments_log(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
    ) -> None:
        """Отключение автопродления при удалении карты фиксируется как отзыв согласия на рекуррентные платежи."""
        api_client.force_authenticate(user=telegram_user)
        api_client.delete(PAYMENT_METHOD_URL)
        assert ConsentLog.objects.filter(
            user=telegram_user,
            consent_type=ConsentType.RECURRING_PAYMENTS,
            action=ConsentAction.REVOKED,
        ).exists()

    def test_delete_without_auto_renew_does_not_create_recurring_payments_log(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
    ) -> None:
        active_subscription_with_period.auto_renew = False
        active_subscription_with_period.save(update_fields=['auto_renew'])
        api_client.force_authenticate(user=telegram_user)
        api_client.delete(PAYMENT_METHOD_URL)
        assert not ConsentLog.objects.filter(
            user=telegram_user,
            consent_type=ConsentType.RECURRING_PAYMENTS,
        ).exists()

    def test_delete_during_trial_clears_pending_tariff(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription_ready_to_charge: Subscription,
    ) -> None:
        """Удаление карты в триале сбрасывает выбранный тариф — триал не перейдёт в оплату."""
        api_client.force_authenticate(user=telegram_user)
        api_client.delete(PAYMENT_METHOD_URL)
        trial_subscription_ready_to_charge.refresh_from_db()
        assert trial_subscription_ready_to_charge.auto_renew is False
        assert trial_subscription_ready_to_charge.pending_tariff is None

    def test_delete_keeps_cancelled_at_if_auto_renew_already_disabled(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
    ) -> None:
        cancelled_at = timezone.now() - timedelta(days=3)
        active_subscription_with_period.auto_renew = False
        active_subscription_with_period.cancelled_at = cancelled_at
        active_subscription_with_period.save(update_fields=['auto_renew', 'cancelled_at'])
        api_client.force_authenticate(user=telegram_user)
        api_client.delete(PAYMENT_METHOD_URL)
        active_subscription_with_period.refresh_from_db()
        assert active_subscription_with_period.cancelled_at == cancelled_at

    def test_rebinding_card_after_period_end_does_not_trigger_renewal(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        """Регресс: карта удалена, период истёк, карта привязана заново — списания быть не должно."""
        api_client.force_authenticate(user=telegram_user)
        api_client.delete(PAYMENT_METHOD_URL)
        new_payment_method = PaymentMethod.objects.create(
            user=telegram_user,
            yookassa_payment_method_id='pm-test-rebound-xxx',
            payment_method_type='bank_card',
            card_last4='5909',
        )
        active_subscription_with_period.refresh_from_db()
        active_subscription_with_period.payment_method = new_payment_method
        active_subscription_with_period.current_period_end = timezone.now() - timedelta(minutes=2)
        active_subscription_with_period.save(update_fields=['payment_method', 'current_period_end'])
        assert ChargeRenewalService()() == 0
        mock_yookassa_payment_create.assert_not_called()
