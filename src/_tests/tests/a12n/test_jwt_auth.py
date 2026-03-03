import pytest

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import User


class TestTelegramA12nJWTService:
    url = reverse('api_v1:a12n:token_telegram_obtain_pair')

    @pytest.mark.usefixtures('mock_tg_validator')
    def test_new_telegram_user_can_get_jwt_token(self, valid_tg_data: dict, api_client: APIClient) -> None:
        User.objects.all().delete()
        response = api_client.post(self.url, headers={'X-TG-INIT-DATA': valid_tg_data})
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
