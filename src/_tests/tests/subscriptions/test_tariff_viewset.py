from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.subscriptions.api.serializers.tariffs import TariffSerializer
from apps.subscriptions.models import Tariff
from apps.subscriptions.models.model_enums import BillingPeriod
from apps.users.models import User

TARIFF_LIST_URL = reverse('api_v1:subscriptions:subscriptions:tariff-list')


def get_tariff_detail_url(tariff_id: str) -> str:
    return reverse('api_v1:subscriptions:subscriptions:tariff-detail', kwargs={'tariff_id': tariff_id})


class TestTariffViewSet:
    def test_anon_user_gets_401(self, api_client: APIClient) -> None:
        response = api_client.get(TARIFF_LIST_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_user_can_list_tariffs(
        self,
        api_client: APIClient,
        telegram_user: User,
        base_tariff: Tariff,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(TARIFF_LIST_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'] == TariffSerializer([base_tariff], many=True).data

    def test_list_only_shows_published_and_active_tariffs(
        self,
        api_client: APIClient,
        telegram_user: User,
        base_tariff: Tariff,
        no_base_features_tariff: Tariff,
    ) -> None:
        """no_base_features_tariff has published=False, so it should not appear."""
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(TARIFF_LIST_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        result_ids = {item['id'] for item in response.data['results']}
        assert str(base_tariff.id) in result_ids
        assert str(no_base_features_tariff.id) not in result_ids

    def test_inactive_tariff_not_listed(
        self,
        api_client: APIClient,
        telegram_user: User,
        base_tariff: Tariff,
    ) -> None:
        base_tariff.is_active = False
        base_tariff.save(update_fields=['is_active'])
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(TARIFF_LIST_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0

    def test_authenticated_user_can_retrieve_tariff(
        self,
        api_client: APIClient,
        telegram_user: User,
        base_tariff: Tariff,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        url = get_tariff_detail_url(str(base_tariff.id))
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == TariffSerializer(base_tariff).data

    def test_anon_user_cannot_retrieve_tariff(
        self,
        api_client: APIClient,
        base_tariff: Tariff,
    ) -> None:
        url = get_tariff_detail_url(str(base_tariff.id))
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_trial_tariff_is_listed(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_tariff: Tariff,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(TARIFF_LIST_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['id'] == str(trial_tariff.id)

    def test_tariff_response_contains_expected_fields(
        self,
        api_client: APIClient,
        telegram_user: User,
        base_tariff: Tariff,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(TARIFF_LIST_URL)
        expected_fields = {
            'id',
            'name',
            'price',
            'billing_period',
            'description',
            'trial_days',
            'can_use_base_features',
            'can_create_ai_recipes',
        }
        assert set(response.data['results'][0].keys()) == expected_fields

    def test_user_without_subscription_can_list_tariffs(
        self,
        api_client: APIClient,
        telegram_user: User,
        base_tariff: Tariff,
    ) -> None:
        """TariffViewSet uses plain JWTAuthentication, not subscription-aware one."""
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(TARIFF_LIST_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_post_method_not_allowed(self, api_client: APIClient, telegram_user: User) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(TARIFF_LIST_URL, data={}, format='json')
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_tariffs_ordered_by_sort_order_and_price(
        self,
        api_client: APIClient,
        telegram_user: User,
    ) -> None:
        expensive = Tariff.objects.create(
            name='Expensive',
            price='99.99',
            billing_period=BillingPeriod.MONTHLY,
            published=True,
            is_active=True,
            can_use_base_features=True,
            can_create_ai_recipes=True,
            sort_order=2,
        )
        cheap = Tariff.objects.create(
            name='Cheap',
            price='9.99',
            billing_period=BillingPeriod.MONTHLY,
            published=True,
            is_active=True,
            can_use_base_features=True,
            can_create_ai_recipes=False,
            sort_order=1,
        )
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(TARIFF_LIST_URL)
        assert response.status_code == status.HTTP_200_OK
        result_ids = [item['id'] for item in response.data['results']]
        assert result_ids.index(str(cheap.id)) < result_ids.index(str(expensive.id))
