import pytest

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.subscriptions.constants import GRACE_PERIOD_DAYS
from apps.subscriptions.models import Subscription, Tariff
from apps.subscriptions.models.model_enums import SubscriptionStatus
from apps.users.models import ConsentLog, User
from apps.users.models.model_enums import ConsentAction, ConsentType


class TestTelegramA12nJWTService:
    url = reverse('api_v1:a12n:token_telegram_obtain_pair')
    protected_url = reverse('api_v1:dishes:dishes:dish-list')

    def _get_access_token(self, api_client: APIClient, valid_tg_data: dict) -> str:
        response = api_client.post(self.url, headers={'X-TG-INIT-DATA': valid_tg_data})
        assert response.status_code == status.HTTP_200_OK
        return response.data['access']

    @pytest.mark.usefixtures('mock_tg_validator')
    def test_new_telegram_user_can_get_jwt_token(self, valid_tg_data: dict, api_client: APIClient) -> None:
        User.objects.all().delete()
        response = api_client.post(
            self.url,
            data={'terms_of_service_and_privacy_policy': True},
            headers={'X-TG-INIT-DATA': valid_tg_data},
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert User.objects.count() == 1

    @pytest.mark.usefixtures('mock_tg_validator')
    def test_existing_telegram_user_can_get_jwt_token(self, valid_tg_data: dict, api_client: APIClient) -> None:
        assert User.objects.count() == 1
        response = api_client.post(self.url, headers={'X-TG-INIT-DATA': valid_tg_data})
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert User.objects.count() == 1

    def test_invalid_tg_data_returns_bad_request(self, api_client: APIClient) -> None:
        response = api_client.post(self.url, headers={'X-TG-INIT-DATA': "{'invalid': 'data'}"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.usefixtures('mock_tg_validator')
    def test_new_user_without_consent_gets_428(self, valid_tg_data: dict, api_client: APIClient) -> None:
        User.objects.all().delete()
        response = api_client.post(self.url, headers={'X-TG-INIT-DATA': valid_tg_data})
        assert response.status_code == status.HTTP_428_PRECONDITION_REQUIRED

    @pytest.mark.usefixtures('mock_tg_validator')
    def test_new_user_with_terms_false_gets_428(self, valid_tg_data: dict, api_client: APIClient) -> None:
        User.objects.all().delete()
        response = api_client.post(
            self.url,
            data={'terms_of_service_and_privacy_policy': False},
            headers={'X-TG-INIT-DATA': valid_tg_data},
        )
        assert response.status_code == status.HTTP_428_PRECONDITION_REQUIRED

    @pytest.mark.usefixtures('mock_tg_validator')
    def test_428_response_has_requires_consent_fields(self, valid_tg_data: dict, api_client: APIClient) -> None:
        User.objects.all().delete()
        response = api_client.post(self.url, headers={'X-TG-INIT-DATA': valid_tg_data})
        assert response.data['requires_consent'] is True
        assert 'consents' in response.data
        assert len(response.data['consents']) > 0

    @pytest.mark.usefixtures('mock_tg_validator')
    def test_new_user_with_consent_creates_tos_and_pp_logs(self, valid_tg_data: dict, api_client: APIClient) -> None:
        User.objects.all().delete()
        api_client.post(
            self.url,
            data={'terms_of_service_and_privacy_policy': True},
            headers={'X-TG-INIT-DATA': valid_tg_data},
        )
        user = User.objects.get()
        assert ConsentLog.objects.filter(
            user=user, consent_type=ConsentType.TERMS_OF_SERVICE, action=ConsentAction.GRANTED
        ).exists()
        assert ConsentLog.objects.filter(
            user=user, consent_type=ConsentType.PRIVACY_POLICY, action=ConsentAction.GRANTED
        ).exists()

    @pytest.mark.usefixtures('mock_tg_validator')
    def test_new_user_with_marketing_true_creates_marketing_log(
        self, valid_tg_data: dict, api_client: APIClient
    ) -> None:
        User.objects.all().delete()
        api_client.post(
            self.url,
            data={'terms_of_service_and_privacy_policy': True, 'marketing_communications': True},
            headers={'X-TG-INIT-DATA': valid_tg_data},
        )
        user = User.objects.get()
        assert ConsentLog.objects.filter(
            user=user, consent_type=ConsentType.MARKETING_COMMUNICATIONS, action=ConsentAction.GRANTED
        ).exists()

    @pytest.mark.usefixtures('mock_tg_validator')
    def test_new_user_with_marketing_true_sets_user_flag(self, valid_tg_data: dict, api_client: APIClient) -> None:
        User.objects.all().delete()
        api_client.post(
            self.url,
            data={'terms_of_service_and_privacy_policy': True, 'marketing_communications': True},
            headers={'X-TG-INIT-DATA': valid_tg_data},
        )
        user = User.objects.get()
        assert user.marketing_communications is True

    @pytest.mark.usefixtures('mock_tg_validator')
    def test_new_user_with_marketing_false_no_marketing_log(self, valid_tg_data: dict, api_client: APIClient) -> None:
        User.objects.all().delete()
        api_client.post(
            self.url,
            data={'terms_of_service_and_privacy_policy': True, 'marketing_communications': False},
            headers={'X-TG-INIT-DATA': valid_tg_data},
        )
        user = User.objects.get()
        assert not ConsentLog.objects.filter(user=user, consent_type=ConsentType.MARKETING_COMMUNICATIONS).exists()
        assert user.marketing_communications is False

    @pytest.mark.usefixtures('mock_tg_validator')
    def test_past_due_subscription_within_grace_period_can_use_protected_endpoint(
        self,
        valid_tg_data: dict,
        api_client: APIClient,
        telegram_user: User,
        paid_tariff: Tariff,
    ) -> None:
        Subscription.objects.create(
            user=telegram_user,
            tariff=paid_tariff,
            status=SubscriptionStatus.PAST_DUE,
            current_period_end=timezone.now() - timedelta(days=GRACE_PERIOD_DAYS - 1),
        )
        access_token = self._get_access_token(api_client, valid_tg_data)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = api_client.get(self.protected_url)
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.usefixtures('mock_tg_validator')
    def test_past_due_subscription_after_grace_period_cannot_use_protected_endpoint(
        self,
        valid_tg_data: dict,
        api_client: APIClient,
        telegram_user: User,
        paid_tariff: Tariff,
    ) -> None:
        Subscription.objects.create(
            user=telegram_user,
            tariff=paid_tariff,
            status=SubscriptionStatus.PAST_DUE,
            current_period_end=timezone.now() - timedelta(days=GRACE_PERIOD_DAYS + 1),
        )
        access_token = self._get_access_token(api_client, valid_tg_data)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = api_client.get(self.protected_url)
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
