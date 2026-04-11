import pytest

from django.utils import timezone

from apps.subscriptions.constants import DEFAULT_TRIAL_DAYS
from apps.subscriptions.models import Subscription, Tariff
from apps.subscriptions.models.model_enums import BillingPeriod, SubscriptionStatus
from apps.users.models import User


@pytest.fixture
def base_tariff() -> Tariff:
    return Tariff.objects.create(
        name='Base',
        price='0.00',
        billing_period=BillingPeriod.MONTHLY,
        published=True,
        is_active=True,
        can_use_base_features=True,
        can_create_ai_recipes=False,
    )


@pytest.fixture
def no_base_features_tariff() -> Tariff:
    return Tariff.objects.create(
        name='No Base Features',
        price='0.00',
        billing_period=BillingPeriod.MONTHLY,
        published=False,
        is_active=True,
        can_use_base_features=False,
        can_create_ai_recipes=False,
    )


@pytest.fixture
def trial_tariff() -> Tariff:
    return Tariff.objects.create(
        name='Trial',
        price='0.00',
        billing_period=BillingPeriod.MONTHLY,
        published=True,
        is_active=True,
        is_trial_tariff=True,
        trial_days=DEFAULT_TRIAL_DAYS,
        can_use_base_features=True,
        can_create_ai_recipes=True,
    )


@pytest.fixture
def active_subscription(telegram_user: User, base_tariff: Tariff) -> Subscription:
    return Subscription.objects.create(
        user=telegram_user,
        tariff=base_tariff,
        status=SubscriptionStatus.ACTIVE,
    )


@pytest.fixture
def another_active_subscription(another_telegram_user: User, base_tariff: Tariff) -> Subscription:
    return Subscription.objects.create(
        user=another_telegram_user,
        tariff=base_tariff,
        status=SubscriptionStatus.ACTIVE,
    )


@pytest.fixture
def trial_subscription(telegram_user: User, trial_tariff: Tariff) -> Subscription:
    return Subscription.objects.create(
        user=telegram_user,
        tariff=trial_tariff,
        status=SubscriptionStatus.TRIAL,
        trial_started_at=timezone.now(),
        days_in_trial=trial_tariff.trial_days,
    )
