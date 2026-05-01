import pytest

from datetime import timedelta

from django.utils import timezone

from apps.subscriptions.constants import DEFAULT_TRIAL_DAYS
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
def expired_subscription(telegram_user: User, paid_tariff: Tariff) -> Subscription:
    return Subscription.objects.create(
        user=telegram_user,
        tariff=paid_tariff,
        status=SubscriptionStatus.EXPIRED,
    )
