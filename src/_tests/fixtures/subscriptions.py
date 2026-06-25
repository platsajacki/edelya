import pytest

from datetime import timedelta

from django.utils import timezone
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from _tests.tests.subscriptions.test_subscription_retry_payment import RETRY_PAYMENT_URL
from apps.subscriptions.constants import DEFAULT_TRIAL_DAYS, GRACE_PERIOD_DAYS
from apps.subscriptions.models import PaymentMethod, Subscription, Tariff
from apps.subscriptions.models.model_enums import BillingPeriod, PaymentStatus, PaymentType, SubscriptionStatus
from apps.subscriptions.models.payments import Payment
from apps.subscriptions.services.webhook_handler import WebhookAction
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
    tariff, _ = Tariff.objects.get_or_create(
        is_trial_tariff=True,
        defaults={
            'name': 'Trial',
            'price': '0.00',
            'billing_period': BillingPeriod.MONTHLY,
            'published': True,
            'is_active': True,
            'trial_days': DEFAULT_TRIAL_DAYS,
            'can_use_base_features': True,
            'can_create_ai_recipes': True,
        },
    )
    return tariff


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


@pytest.fixture
def paid_tariff() -> Tariff:
    return Tariff.objects.create(
        name='Paid',
        price='99.00',
        billing_period=BillingPeriod.MONTHLY,
        published=True,
        is_active=True,
        is_trial_tariff=False,
        can_use_base_features=True,
        can_create_ai_recipes=True,
    )


@pytest.fixture
def active_payment_method(telegram_user: User) -> PaymentMethod:
    return PaymentMethod.objects.create(
        user=telegram_user,
        yookassa_payment_method_id='pm-test-active-xxx',
        payment_method_type='bank_card',
        card_last4='4242',
        card_type='Visa',
        is_active=True,
    )


@pytest.fixture
def trial_subscription_with_payment_method(
    telegram_user: User,
    trial_tariff: Tariff,
    active_payment_method: PaymentMethod,
) -> Subscription:
    return Subscription.objects.create(
        user=telegram_user,
        tariff=trial_tariff,
        status=SubscriptionStatus.TRIAL,
        trial_started_at=timezone.now(),
        days_in_trial=trial_tariff.trial_days,
        payment_method=active_payment_method,
    )


@pytest.fixture
def upgrade_tariff() -> Tariff:
    tariff, _ = Tariff.objects.get_or_create(
        name='Premium',
        defaults={
            'price': '199.00',
            'billing_period': BillingPeriod.MONTHLY,
            'published': True,
            'is_active': True,
            'is_trial_tariff': False,
            'can_use_base_features': True,
            'can_create_ai_recipes': True,
        },
    )
    return tariff


@pytest.fixture
def active_subscription_with_period(
    telegram_user: User,
    paid_tariff: Tariff,
    active_payment_method: PaymentMethod,
) -> Subscription:
    now = timezone.now()
    return Subscription.objects.create(
        user=telegram_user,
        tariff=paid_tariff,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now - timedelta(days=15),
        current_period_end=now + timedelta(days=15),
        payment_method=active_payment_method,
    )


@pytest.fixture
def pending_payment_zero_amount(telegram_user: User, trial_subscription: Subscription) -> Payment:
    return Payment.objects.create(
        subscription=trial_subscription,
        user=telegram_user,
        amount=0,
        payment_type=PaymentType.ZERO_AMOUNT_BINDING,
        status=PaymentStatus.PENDING,
        idempotence_key='11111111-1111-1111-1111-111111111111',
        yookassa_payment_id='yoo-pm-id-001',
        metadata={'action': WebhookAction.TRIAL_CARD_BINDING, 'tariff_id': None},
    )


@pytest.fixture
def pending_payment_zero_amount_with_tariff(
    telegram_user: User,
    trial_subscription: Subscription,
    paid_tariff: Tariff,
) -> Payment:
    return Payment.objects.create(
        subscription=trial_subscription,
        user=telegram_user,
        amount=0,
        payment_type=PaymentType.ZERO_AMOUNT_BINDING,
        status=PaymentStatus.PENDING,
        idempotence_key='22222222-2222-2222-2222-222222222222',
        yookassa_payment_id='yoo-pm-id-001',
        metadata={'action': WebhookAction.TRIAL_CARD_BINDING, 'tariff_id': str(paid_tariff.id)},
    )


@pytest.fixture
def pending_payment_first(
    telegram_user: User,
    expired_subscription: Subscription,
    paid_tariff: Tariff,
) -> Payment:
    return Payment.objects.create(
        subscription=expired_subscription,
        user=telegram_user,
        amount=paid_tariff.price,
        payment_type=PaymentType.FIRST_PAYMENT,
        status=PaymentStatus.PENDING,
        idempotence_key='33333333-3333-3333-3333-333333333333',
        yookassa_payment_id='yoo-pay-id-001',
        metadata={'action': WebhookAction.FIRST_PAYMENT, 'tariff_id': str(paid_tariff.id)},
    )


@pytest.fixture
def pending_payment_recurring(
    telegram_user: User,
    active_subscription_with_period: Subscription,
    paid_tariff: Tariff,
) -> Payment:
    return Payment.objects.create(
        subscription=active_subscription_with_period,
        user=telegram_user,
        amount=paid_tariff.price,
        payment_type=PaymentType.RECURRING,
        status=PaymentStatus.PENDING,
        idempotence_key='44444444-4444-4444-4444-444444444444',
        yookassa_payment_id='yoo-pay-id-recurring-001',
        metadata={'action': WebhookAction.RECURRING},
    )


@pytest.fixture
def pending_payment_upgrade(
    telegram_user: User,
    active_subscription_with_period: Subscription,
    upgrade_tariff: Tariff,
    active_payment_method: PaymentMethod,
) -> Payment:
    return Payment.objects.create(
        subscription=active_subscription_with_period,
        user=telegram_user,
        amount='50.00',
        payment_type=PaymentType.SINGLE_PAYMENT,
        status=PaymentStatus.PENDING,
        idempotence_key='55555555-5555-5555-5555-555555555555',
        yookassa_payment_id='yoo-pay-id-upgrade-001',
        payment_method=active_payment_method,
        metadata={'action': WebhookAction.UPGRADE, 'tariff_id': str(upgrade_tariff.id)},
    )


@pytest.fixture
def expired_subscription(telegram_user: User, paid_tariff: Tariff) -> Subscription:
    return Subscription.objects.create(
        user=telegram_user,
        tariff=paid_tariff,
        status=SubscriptionStatus.EXPIRED,
    )


@pytest.fixture
def trial_subscription_ready_to_charge(
    telegram_user: User,
    trial_tariff: Tariff,
    paid_tariff: Tariff,
    active_payment_method: PaymentMethod,
) -> Subscription:
    """TRIAL subscription whose trial ended 10 minutes ago, ready for charge."""
    return Subscription.objects.create(
        user=telegram_user,
        tariff=trial_tariff,
        status=SubscriptionStatus.TRIAL,
        trial_started_at=timezone.now() - timedelta(days=trial_tariff.trial_days),
        days_in_trial=trial_tariff.trial_days,
        trial_ended_at=timezone.now() - timedelta(minutes=10),
        pending_tariff=paid_tariff,
        payment_method=active_payment_method,
    )


@pytest.fixture
def pending_recurring_payment_for_trial(
    telegram_user: User,
    trial_subscription_ready_to_charge: Subscription,
) -> Payment:
    """PENDING RECURRING payment already created for trial_subscription_ready_to_charge."""
    return Payment.objects.create(
        subscription=trial_subscription_ready_to_charge,
        user=telegram_user,
        amount='99.00',
        payment_type=PaymentType.RECURRING,
        status=PaymentStatus.PENDING,
        idempotence_key='66666666-6666-6666-6666-666666666666',
        metadata={'action': WebhookAction.FIRST_PAYMENT},
    )


@pytest.fixture
def active_subscription_ready_to_renew(
    telegram_user: User,
    paid_tariff: Tariff,
    active_payment_method: PaymentMethod,
) -> Subscription:
    """ACTIVE subscription with auto_renew=True whose period ended 2 minutes ago — within charge window."""
    now = timezone.now()
    return Subscription.objects.create(
        user=telegram_user,
        tariff=paid_tariff,
        status=SubscriptionStatus.ACTIVE,
        auto_renew=True,
        current_period_start=now - timedelta(days=30),
        current_period_end=now - timedelta(minutes=2),
        payment_method=active_payment_method,
    )


@pytest.fixture
def pending_recurring_payment_for_renewal(
    telegram_user: User,
    active_subscription_ready_to_renew: Subscription,
) -> Payment:
    """PENDING RECURRING payment already created for active_subscription_ready_to_renew."""
    return Payment.objects.create(
        subscription=active_subscription_ready_to_renew,
        user=telegram_user,
        amount='99.00',
        payment_type=PaymentType.RECURRING,
        status=PaymentStatus.PENDING,
        idempotence_key='77777777-7777-7777-7777-777777777777',
        metadata={'action': WebhookAction.RECURRING},
    )


@pytest.fixture
def past_due_subscription_ready_for_retry(
    telegram_user: User,
    paid_tariff: Tariff,
    active_payment_method: PaymentMethod,
) -> Subscription:
    """PAST_DUE subscription whose grace period expires within the next 5 minutes — time for retry."""
    now = timezone.now()
    period_start = now - timedelta(days=GRACE_PERIOD_DAYS) + timedelta(minutes=2)
    return Subscription.objects.create(
        user=telegram_user,
        tariff=paid_tariff,
        status=SubscriptionStatus.PAST_DUE,
        current_period_start=period_start,
        current_period_end=paid_tariff.get_next_period_end(period_start),
        payment_method=active_payment_method,
    )


@pytest.fixture
def pending_recurring_payment_for_past_due(
    telegram_user: User,
    past_due_subscription_ready_for_retry: Subscription,
) -> Payment:
    """PENDING RECURRING payment already created for past_due_subscription_ready_for_retry."""
    return Payment.objects.create(
        subscription=past_due_subscription_ready_for_retry,
        user=telegram_user,
        amount='99.00',
        payment_type=PaymentType.RECURRING,
        status=PaymentStatus.PENDING,
        idempotence_key='88888888-8888-8888-8888-888888888888',
        metadata={'action': WebhookAction.RECURRING},
    )


@pytest.fixture
def abandoned_trial_subscription(
    telegram_user: User,
    trial_tariff: Tariff,
) -> Subscription:
    """TRIAL subscription with expired trial and no pending_tariff — will never become ACTIVE."""
    return Subscription.objects.create(
        user=telegram_user,
        tariff=trial_tariff,
        status=SubscriptionStatus.TRIAL,
        trial_started_at=timezone.now() - timedelta(days=trial_tariff.trial_days + 1),
        days_in_trial=trial_tariff.trial_days,
        trial_ended_at=timezone.now() - timedelta(hours=1),
        pending_tariff=None,
    )


@pytest.fixture
def past_due_subscription_for_expiry(
    telegram_user: User,
    paid_tariff: Tariff,
) -> Subscription:
    """PAST_DUE subscription whose grace period has already expired — ready for final expiry."""
    now = timezone.now()
    period_start = now - timedelta(days=GRACE_PERIOD_DAYS + 1)
    return Subscription.objects.create(
        user=telegram_user,
        tariff=paid_tariff,
        status=SubscriptionStatus.PAST_DUE,
        current_period_start=period_start,
        current_period_end=paid_tariff.get_next_period_end(period_start),
    )


@pytest.fixture
def cancelled_subscription_ready_to_expire(
    telegram_user: User,
    paid_tariff: Tariff,
) -> Subscription:
    """ACTIVE subscription with auto_renew=False whose paid period has ended — ready for expiry."""
    now = timezone.now()
    return Subscription.objects.create(
        user=telegram_user,
        tariff=paid_tariff,
        status=SubscriptionStatus.ACTIVE,
        auto_renew=False,
        current_period_start=now - timedelta(days=31),
        current_period_end=now - timedelta(days=1),
    )


@pytest.fixture
def payment_ready_for_check(
    telegram_user: User,
    active_subscription_with_period: Subscription,
    paid_tariff: Tariff,
) -> Payment:
    """SUCCEEDED payment with send_to_tax3r=True and is_check_sent=False — ready for Tax3r check processing."""
    return Payment.objects.create(
        subscription=active_subscription_with_period,
        user=telegram_user,
        amount=paid_tariff.price,
        payment_type=PaymentType.RECURRING,
        status=PaymentStatus.SUCCEEDED,
        idempotence_key='99999999-9999-9999-9999-999999999999',
        yookassa_payment_id='yoo-pay-id-tax3r-001',
        send_to_tax3r=True,
        is_check_sent=False,
        metadata={'action': 'recurring'},
    )


@pytest.fixture
def expired_subscription_with_payment_method(
    telegram_user: User,
    paid_tariff: Tariff,
    active_payment_method: PaymentMethod,
) -> Subscription:
    now = timezone.now()
    return Subscription.objects.create(
        user=telegram_user,
        tariff=paid_tariff,
        status=SubscriptionStatus.EXPIRED,
        current_period_start=now - timedelta(days=60),
        current_period_end=now - timedelta(days=30),
        payment_method=active_payment_method,
    )


@pytest.fixture
def retry_payment_request(telegram_user: User) -> Request:
    request = APIRequestFactory().post(RETRY_PAYMENT_URL)
    request.user = telegram_user
    return request
