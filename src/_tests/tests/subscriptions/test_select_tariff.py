import pytest
from pytest_mock import MockType

import uuid
from decimal import Decimal
from unittest.mock import MagicMock

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.subscriptions.models import PaymentMethod, Subscription, Tariff
from apps.subscriptions.models.model_enums import PaymentStatus, PaymentType, SubscriptionStatus
from apps.subscriptions.models.payments import Payment
from apps.users.models import User

SELECT_TARIFF_URL = reverse('api_v1:subscriptions:subscriptions:subscription-select-tariff')


class TestSelectTariff:
    def test_anon_user_gets_401(self, api_client: APIClient) -> None:
        response = api_client.post(SELECT_TARIFF_URL, data={}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_without_subscription_gets_404(
        self,
        api_client: APIClient,
        telegram_user: User,
        paid_tariff: Tariff,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(SELECT_TARIFF_URL, data={'tariff_id': str(paid_tariff.id)}, format='json')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_payload_gets_400(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(SELECT_TARIFF_URL, data={}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_nonexistent_tariff_id_gets_404(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(uuid.uuid4())},
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_trial_tariff_not_selectable_gets_404(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
        trial_tariff: Tariff,
    ) -> None:
        """Trial tariff is excluded from actual() queryset via is_trial_tariff=False filter."""
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(trial_tariff.id)},
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unpublished_tariff_gets_404(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
    ) -> None:
        unpublished = Tariff.objects.create(
            name='Unpublished Paid',
            price='49.00',
            published=False,
            is_active=True,
            is_trial_tariff=False,
            can_use_base_features=True,
        )
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(unpublished.id)},
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_inactive_tariff_gets_404(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
    ) -> None:
        inactive = Tariff.objects.create(
            name='Inactive Paid',
            price='49.00',
            published=True,
            is_active=False,
            is_trial_tariff=False,
            can_use_base_features=True,
        )
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(inactive.id)},
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_selecting_current_tariff_gets_409(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription: Subscription,
        base_tariff: Tariff,
    ) -> None:
        """Selecting the tariff the user is already subscribed to → ConflictError."""
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(base_tariff.id)},
            format='json',
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_trial_selecting_pending_same_tariff_gets_409(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        """If pending_tariff is already set to the requested tariff → ConflictError."""
        trial_subscription.pending_tariff = paid_tariff
        trial_subscription.save(update_fields=['pending_tariff'])
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(paid_tariff.id)},
            format='json',
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_trial_with_payment_method_schedules_pending_tariff(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription_with_payment_method: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        """TRIAL + active payment_method → TrialTariffScheduler sets pending_tariff."""
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(paid_tariff.id)},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        trial_subscription_with_payment_method.refresh_from_db()
        assert trial_subscription_with_payment_method.pending_tariff == paid_tariff

    def test_trial_with_payment_method_response_structure(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription_with_payment_method: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        """SuccessResponse has action='success' and contains serialized subscription."""
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(paid_tariff.id)},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['action'] == 'success'
        assert 'subscription' in response.data

    def test_trial_without_payment_method_redirects_to_card_binding(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
        paid_tariff: Tariff,
        mock_yookassa_payment_method_create: MockType,
    ) -> None:
        """TRIAL + no payment_method → TrialTariffBinder redirects to card binding."""
        fake_payment_method = MagicMock()
        fake_payment_method.id = 'yoo-pm-id-789'
        fake_payment_method.confirmation.confirmation_url = 'https://yookassa.ru/bind/789'
        mock_yookassa_payment_method_create.return_value = fake_payment_method
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(paid_tariff.id)},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['action'] == 'redirect'
        assert response.data['confirmation_url'] == 'https://yookassa.ru/bind/789'
        assert response.data['context'] == 'card_binding'

    def test_trial_without_payment_method_creates_payment_record(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
        paid_tariff: Tariff,
        mock_yookassa_payment_method_create: MockType,
    ) -> None:
        """TrialTariffBinder creates a Payment(ZERO_AMOUNT_BINDING) with tariff_id in metadata."""
        fake_payment_method = MagicMock()
        fake_payment_method.id = 'yoo-pm-id-abc'
        fake_payment_method.confirmation.confirmation_url = 'https://yookassa.ru/bind/abc'
        mock_yookassa_payment_method_create.return_value = fake_payment_method
        api_client.force_authenticate(user=telegram_user)
        api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(paid_tariff.id)},
            format='json',
        )
        payment = Payment.objects.get(yookassa_payment_id='yoo-pm-id-abc')
        assert payment.subscription == trial_subscription
        assert payment.user == telegram_user
        assert payment.amount == 0
        assert payment.payment_type == PaymentType.ZERO_AMOUNT_BINDING
        assert payment.status == PaymentStatus.PENDING
        assert payment.metadata['tariff_id'] == str(paid_tariff.id)

    def test_active_upgrade_no_payment_method_gets_409(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        """ACTIVE + no payment_method + upgrade → 409 with message to update payment info."""
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(paid_tariff.id)},
            format='json',
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_active_downgrade_sets_pending_tariff(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        base_tariff: Tariff,
    ) -> None:
        """ACTIVE + paid → base (downgrade) → sets pending_tariff, returns success."""
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(base_tariff.id)},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['action'] == 'success'
        active_subscription_with_period.refresh_from_db()
        assert active_subscription_with_period.pending_tariff == base_tariff

    def test_active_downgrade_pending_same_tariff_gets_409(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        base_tariff: Tariff,
    ) -> None:
        """Downgrade with pending_tariff already = target → ConflictError 409."""
        active_subscription_with_period.pending_tariff = base_tariff
        active_subscription_with_period.save(update_fields=['pending_tariff'])
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(base_tariff.id)},
            format='json',
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_active_upgrade_creates_recurring_payment(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        upgrade_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        """ACTIVE + proration > 0 → Payment(RECURRING) created with proportional amount."""
        fake_payment = MagicMock()
        fake_payment.id = 'yoo-upgrade-pay-001'
        fake_payment.status = 'pending'
        mock_yookassa_payment_create.return_value = fake_payment
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(upgrade_tariff.id)},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['action'] == 'success'
        payment = Payment.objects.get(yookassa_payment_id='yoo-upgrade-pay-001')
        assert payment.payment_type == PaymentType.RECURRING
        assert payment.status == PaymentStatus.PENDING
        assert payment.user == telegram_user
        assert payment.metadata['tariff_id'] == str(upgrade_tariff.id)
        # proration = remaining_days/30 * (199-99); remaining ≈ 14-15 days → ~46-50 RUB
        assert Decimal('0') < payment.amount < Decimal('100.00')

    def test_active_upgrade_switches_tariff_and_resets_period(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        upgrade_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        """ACTIVE upgrade → tariff switched, period reset to now."""
        fake_payment = MagicMock()
        fake_payment.id = 'yoo-upgrade-pay-002'
        fake_payment.status = 'pending'
        mock_yookassa_payment_create.return_value = fake_payment
        before = timezone.now()
        api_client.force_authenticate(user=telegram_user)
        api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(upgrade_tariff.id)},
            format='json',
        )
        active_subscription_with_period.refresh_from_db()
        assert active_subscription_with_period.tariff == upgrade_tariff
        assert active_subscription_with_period.current_period_start is not None
        assert active_subscription_with_period.current_period_start >= before
        assert active_subscription_with_period.current_period_end is not None
        assert active_subscription_with_period.current_period_end > active_subscription_with_period.current_period_start

    def test_active_upgrade_no_period_switches_without_payment(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_payment_method: PaymentMethod,
        upgrade_tariff: Tariff,
        base_tariff: Tariff,
    ) -> None:
        """ACTIVE upgrade with no period info → proration=0 → tariff switched, no Payment created."""
        subscription = Subscription.objects.create(
            user=telegram_user,
            tariff=base_tariff,
            status=SubscriptionStatus.ACTIVE,
            payment_method=active_payment_method,
            # current_period_start/end intentionally left None
        )
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(upgrade_tariff.id)},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['action'] == 'success'
        subscription.refresh_from_db()
        assert subscription.tariff == upgrade_tariff
        assert Payment.objects.count() == 0

    def test_active_upgrade_canceled_payment_saves_record_and_gets_409(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        upgrade_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        """YooKassa returns canceled → Payment saved with CANCELED status, 409 returned."""
        fake_payment = MagicMock()
        fake_payment.id = 'yoo-upgrade-pay-canceled'
        fake_payment.status = 'canceled'
        mock_yookassa_payment_create.return_value = fake_payment
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(upgrade_tariff.id)},
            format='json',
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        payment = Payment.objects.get(yookassa_payment_id='yoo-upgrade-pay-canceled')
        assert payment.status == PaymentStatus.CANCELED

    def test_active_upgrade_payment_has_is_upgrade_in_metadata(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        upgrade_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        """Upgrade payment metadata contains is_upgrade=True for webhook handler identification."""
        fake_payment = MagicMock()
        fake_payment.id = 'yoo-upgrade-pay-meta'
        fake_payment.status = 'pending'
        mock_yookassa_payment_create.return_value = fake_payment
        api_client.force_authenticate(user=telegram_user)
        api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(upgrade_tariff.id)},
            format='json',
        )
        payment = Payment.objects.get(yookassa_payment_id='yoo-upgrade-pay-meta')
        assert payment.metadata.get('is_upgrade') is True
        assert payment.metadata.get('tariff_id') == str(upgrade_tariff.id)

    @pytest.mark.parametrize('sub_status', [SubscriptionStatus.EXPIRED, SubscriptionStatus.CANCELLED])
    def test_expired_or_cancelled_redirects_to_payment(
        self,
        api_client: APIClient,
        telegram_user: User,
        base_tariff: Tariff,
        paid_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
        sub_status: SubscriptionStatus,
    ) -> None:
        """EXPIRED/CANCELLED → TariffActivator redirects to payment confirmation."""
        fake_payment = MagicMock()
        fake_payment.id = 'yoo-payment-id-123'
        fake_payment.confirmation.confirmation_url = 'https://yookassa.ru/pay/123'
        mock_yookassa_payment_create.return_value = fake_payment
        Subscription.objects.create(
            user=telegram_user,
            tariff=base_tariff,
            status=sub_status,
        )
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(paid_tariff.id)},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['action'] == 'redirect'
        assert response.data['confirmation_url'] == 'https://yookassa.ru/pay/123'
        assert response.data['context'] == 'payment'

    @pytest.mark.parametrize('sub_status', [SubscriptionStatus.EXPIRED, SubscriptionStatus.CANCELLED])
    def test_expired_or_cancelled_creates_payment_record(
        self,
        api_client: APIClient,
        telegram_user: User,
        base_tariff: Tariff,
        paid_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
        sub_status: SubscriptionStatus,
    ) -> None:
        """TariffActivator creates a Payment record with correct fields."""
        fake_payment = MagicMock()
        fake_payment.id = 'yoo-payment-id-456'
        fake_payment.confirmation.confirmation_url = 'https://yookassa.ru/pay/456'
        mock_yookassa_payment_create.return_value = fake_payment
        subscription = Subscription.objects.create(
            user=telegram_user,
            tariff=base_tariff,
            status=sub_status,
        )
        api_client.force_authenticate(user=telegram_user)
        api_client.post(
            SELECT_TARIFF_URL,
            data={'tariff_id': str(paid_tariff.id)},
            format='json',
        )
        payment = Payment.objects.get(yookassa_payment_id='yoo-payment-id-456')
        assert payment.subscription == subscription
        assert payment.user == telegram_user
        assert payment.amount == Decimal(paid_tariff.price)
        assert payment.payment_type == PaymentType.FIRST_PAYMENT
        assert payment.status == PaymentStatus.PENDING
        assert payment.metadata['tariff_id'] == str(paid_tariff.id)

    def test_get_method_not_allowed(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.get(SELECT_TARIFF_URL)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
