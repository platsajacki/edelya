from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.subscriptions.models import Subscription, Tariff
from apps.subscriptions.models.model_enums import SubscriptionStatus
from apps.users.models import User

SUBSCRIPTION_ME_URL = reverse('api_v1:subscriptions:subscriptions:subscription-me')
START_TRIAL_URL = reverse('api_v1:subscriptions:subscriptions:subscription-start-trial')


class TestSubscriptionMe:
    def test_anon_user_gets_401(self, api_client: APIClient) -> None:
        response = api_client.get(SUBSCRIPTION_ME_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_without_subscription_gets_404(self, api_client: APIClient, telegram_user: User) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(SUBSCRIPTION_ME_URL)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_user_with_active_subscription_gets_200(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription: Subscription,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(SUBSCRIPTION_ME_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(active_subscription.id)
        assert response.data['status'] == SubscriptionStatus.ACTIVE

    def test_response_contains_nested_tariff(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription: Subscription,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(SUBSCRIPTION_ME_URL)
        assert response.status_code == status.HTTP_200_OK
        tariff_data = response.data['tariff']
        assert tariff_data['id'] == str(active_subscription.tariff.id)
        assert tariff_data['name'] == active_subscription.tariff.name

    def test_user_with_trial_subscription_gets_200(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(SUBSCRIPTION_ME_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == SubscriptionStatus.TRIAL
        assert response.data['is_active'] is True

    def test_response_contains_expected_fields(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription: Subscription,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(SUBSCRIPTION_ME_URL)
        expected_fields = {
            'id',
            'status',
            'tariff',
            'trial_started_at',
            'days_in_trial',
            'trial_ended_at',
            'current_period_start',
            'current_period_end',
            'auto_renew',
            'is_active',
            'created_at',
            'updated_at',
        }
        assert set(response.data.keys()) == expected_fields


class TestStartTrial:
    def test_anon_user_gets_401(self, api_client: APIClient) -> None:
        response = api_client.post(START_TRIAL_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_without_subscription_can_start_trial(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_tariff: Tariff,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(START_TRIAL_URL)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == SubscriptionStatus.TRIAL
        assert response.data['tariff']['id'] == str(trial_tariff.id)
        assert Subscription.objects.filter(user=telegram_user).exists()

    def test_trial_creates_subscription_with_correct_fields(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_tariff: Tariff,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(START_TRIAL_URL)
        assert response.status_code == status.HTTP_201_CREATED
        subscription = Subscription.objects.get(user=telegram_user)
        assert subscription.status == SubscriptionStatus.TRIAL
        assert subscription.tariff == trial_tariff
        assert subscription.trial_started_at is not None
        assert subscription.days_in_trial == trial_tariff.trial_days

    def test_user_with_existing_subscription_gets_400(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription: Subscription,
        trial_tariff: Tariff,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(START_TRIAL_URL)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_user_with_trial_subscription_cannot_start_again(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(START_TRIAL_URL)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Subscription.objects.filter(user=telegram_user).count() == 1

    def test_start_trial_without_trial_tariff_gets_404(
        self,
        api_client: APIClient,
        telegram_user: User,
    ) -> None:
        # Deactivate the migration-seeded trial tariff to simulate no available trial
        Tariff.objects.filter(is_trial_tariff=True).update(is_active=False)
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(START_TRIAL_URL)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_start_trial_response_contains_nested_tariff(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_tariff: Tariff,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(START_TRIAL_URL)
        assert response.status_code == status.HTTP_201_CREATED
        tariff_data = response.data['tariff']
        assert tariff_data['name'] == trial_tariff.name
        assert tariff_data['can_use_base_features'] == trial_tariff.can_use_base_features
        assert tariff_data['can_create_ai_recipes'] == trial_tariff.can_create_ai_recipes

    def test_get_method_not_allowed_on_start_trial(self, api_client: APIClient, telegram_user: User) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(START_TRIAL_URL)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_post_method_not_allowed_on_me(self, api_client: APIClient, telegram_user: User) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(SUBSCRIPTION_ME_URL)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
