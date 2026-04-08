
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import User

URL = reverse('api_v1:users:user-onboarding-data')


class TestOnboardingDataRetrieve:
    def test_unauthenticated_returns_401(self, api_client: APIClient) -> None:
        response = api_client.get(URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_empty_dict_by_default(self, auth_telegram_api_client: APIClient, telegram_user: User) -> None:
        response = auth_telegram_api_client.get(URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['onboarding_data'] == {}

    def test_returns_existing_onboarding_data(self, auth_telegram_api_client: APIClient, telegram_user: User) -> None:
        telegram_user.onboarding_data = {'intro': True, 'profile': False}
        telegram_user.save()
        response = auth_telegram_api_client.get(URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['onboarding_data'] == {'intro': True, 'profile': False}


class TestOnboardingDataUpdate:
    def test_unauthenticated_returns_401(self, api_client: APIClient) -> None:
        response = api_client.patch(URL, data={'onboarding_data': {'intro': True}}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_can_add_new_keys(self, auth_telegram_api_client: APIClient, telegram_user: User) -> None:
        response = auth_telegram_api_client.patch(
            URL,
            data={'onboarding_data': {'intro': True}},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['onboarding_data'] == {'intro': True}
        telegram_user.refresh_from_db()
        assert telegram_user.onboarding_data == {'intro': True}

    def test_can_change_existing_key_value(self, auth_telegram_api_client: APIClient, telegram_user: User) -> None:
        telegram_user.onboarding_data = {'intro': False}
        telegram_user.save()
        response = auth_telegram_api_client.patch(
            URL,
            data={'onboarding_data': {'intro': True}},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['onboarding_data']['intro'] is True

    def test_can_add_key_alongside_existing_ones(
        self, auth_telegram_api_client: APIClient, telegram_user: User
    ) -> None:
        telegram_user.onboarding_data = {'intro': True}
        telegram_user.save()
        response = auth_telegram_api_client.patch(
            URL,
            data={'onboarding_data': {'intro': True, 'profile': True}},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['onboarding_data'] == {'intro': True, 'profile': True}

    def test_cannot_remove_existing_key(self, auth_telegram_api_client: APIClient, telegram_user: User) -> None:
        telegram_user.onboarding_data = {'intro': True, 'profile': False}
        telegram_user.save()
        response = auth_telegram_api_client.patch(
            URL,
            data={'onboarding_data': {'intro': True}},  # 'profile' removed
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_boolean_value_returns_400(self, auth_telegram_api_client: APIClient) -> None:
        response = auth_telegram_api_client.patch(
            URL,
            data={'onboarding_data': {'intro': 'yes'}},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_integer_value_returns_400(self, auth_telegram_api_client: APIClient) -> None:
        response = auth_telegram_api_client.patch(
            URL,
            data={'onboarding_data': {'intro': 1}},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_null_value_returns_400(self, auth_telegram_api_client: APIClient) -> None:
        response = auth_telegram_api_client.patch(
            URL,
            data={'onboarding_data': {'intro': None}},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_dict_value_returns_400(self, auth_telegram_api_client: APIClient) -> None:
        response = auth_telegram_api_client.patch(
            URL,
            data={'onboarding_data': ['intro', True]},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
