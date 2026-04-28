from pytest_mock import MockType

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.subscriptions.models import PaymentMethod
from apps.users.models import User

PAYMENT_METHOD_URL = reverse('api_v1:subscriptions:payment-method')


class TestPaymentMethodCreate:
    def test_anon_user_gets_401(self, api_client: APIClient) -> None:
        response = api_client.post(PAYMENT_METHOD_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_user_gets_200(
        self,
        api_client: APIClient,
        telegram_user: User,
        mock_yookassa_payment_method_create: MockType,
    ) -> None:
        mock_yookassa_payment_method_create.return_value.confirmation.confirmation_url = 'https://yookassa.ru/pay'
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(PAYMENT_METHOD_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_response_is_redirect_with_card_binding_context(
        self,
        api_client: APIClient,
        telegram_user: User,
        mock_yookassa_payment_method_create: MockType,
    ) -> None:
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
        mock_yookassa_payment_method_create: MockType,
    ) -> None:
        mock_yookassa_payment_method_create.return_value.confirmation.confirmation_url = 'https://yookassa.ru/pay'
        api_client.force_authenticate(user=telegram_user)
        api_client.post(PAYMENT_METHOD_URL)
        mock_yookassa_payment_method_create.assert_called_once()


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
