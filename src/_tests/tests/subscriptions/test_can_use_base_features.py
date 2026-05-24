from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.subscriptions.models import Subscription, Tariff
from apps.subscriptions.models.model_enums import SubscriptionStatus
from apps.users.models import User

DISHES_LIST_URL = reverse('api_v1:dishes:dishes:dish-list')


class TestCanUseBaseFeatures:
    """Tests for CanUseBaseFeatures permission on all protected endpoints."""

    def test_user_without_subscription_gets_403(self, api_client: APIClient, telegram_user: User) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(DISHES_LIST_URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_with_can_use_base_features_false_gets_403(
        self,
        api_client: APIClient,
        telegram_user: User,
        no_base_features_tariff: Tariff,
    ) -> None:
        Subscription.objects.create(
            user=telegram_user,
            tariff=no_base_features_tariff,
            status=SubscriptionStatus.ACTIVE,
        )
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(DISHES_LIST_URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_with_can_use_base_features_true_gets_200(
        self,
        auth_telegram_api_client: APIClient,
    ) -> None:
        response = auth_telegram_api_client.get(DISHES_LIST_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_unauthenticated_user_gets_401(self, api_client: APIClient) -> None:
        response = api_client.get(DISHES_LIST_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_with_inactive_tariff_still_allowed_if_flag_is_true(
        self,
        api_client: APIClient,
        telegram_user: User,
        base_tariff: Tariff,
    ) -> None:
        """CanUseBaseFeatures only checks the tariff flag, not subscription status."""
        base_tariff.is_active = False
        base_tariff.save()
        Subscription.objects.create(
            user=telegram_user,
            tariff=base_tariff,
            status=SubscriptionStatus.ACTIVE,
        )
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(DISHES_LIST_URL)
        assert response.status_code == status.HTTP_200_OK
