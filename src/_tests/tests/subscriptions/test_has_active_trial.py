from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.subscriptions.constants import DEFAULT_TRIAL_DAYS
from apps.subscriptions.models import Subscription, Tariff
from apps.subscriptions.models.model_enums import SubscriptionStatus
from apps.users.models import User

DISHES_LIST_URL = reverse('api_v1:dishes:dishes:dish-list')


class TestHasActiveTrial:
    """Tests for HasActiveTrial permission granting access via trial subscription."""

    def test_user_with_active_trial_gets_200(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(DISHES_LIST_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_user_with_expired_trial_gets_403(
        self,
        api_client: APIClient,
        telegram_user: User,
    ) -> None:
        trial_tariff = Tariff.objects.get(is_trial_tariff=True)
        trial_tariff.can_use_base_features = False
        trial_tariff.save(update_fields=['can_use_base_features'])
        Subscription.objects.create(
            user=telegram_user,
            tariff=trial_tariff,
            status=SubscriptionStatus.TRIAL,
            trial_started_at=timezone.now() - timedelta(days=DEFAULT_TRIAL_DAYS + 1),
            days_in_trial=DEFAULT_TRIAL_DAYS,
        )
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(DISHES_LIST_URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_with_cancelled_trial_subscription_gets_403(
        self,
        api_client: APIClient,
        telegram_user: User,
    ) -> None:
        trial_tariff = Tariff.objects.get(is_trial_tariff=True)
        trial_tariff.can_use_base_features = False
        trial_tariff.save(update_fields=['can_use_base_features'])
        Subscription.objects.create(
            user=telegram_user,
            tariff=trial_tariff,
            status=SubscriptionStatus.CANCELLED,
            trial_started_at=timezone.now(),
            days_in_trial=DEFAULT_TRIAL_DAYS,
        )
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(DISHES_LIST_URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_with_non_trial_tariff_not_granted_trial_access(
        self,
        api_client: APIClient,
        telegram_user: User,
        no_base_features_tariff: Tariff,
    ) -> None:
        """User with a non-trial tariff that has can_use_base_features=False should get 403."""
        Subscription.objects.create(
            user=telegram_user,
            tariff=no_base_features_tariff,
            status=SubscriptionStatus.ACTIVE,
        )
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(DISHES_LIST_URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_trial_permission_works_as_alternative_to_base_features(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
    ) -> None:
        """Trial tariff has can_use_base_features=True but also is_trial_tariff=True.
        Even if CanUseBaseFeatures alone would grant access, HasActiveTrial should too."""
        # Verify the trial tariff has the trial flag
        assert trial_subscription.tariff.is_trial_tariff is True
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(DISHES_LIST_URL)
        assert response.status_code == status.HTTP_200_OK
