from pytest_mock import MockFixture

from datetime import timedelta

from django.utils import timezone

from apps.subscriptions.models import Subscription, Tariff
from apps.subscriptions.models.model_enums import SubscriptionStatus
from apps.subscriptions.tasks.expire import (
    ExpireCancelledService,
    ExpirePastDueService,
    ExpireTrialsService,
    expire_cancelled_subscriptions,
    expire_past_due_subscriptions,
    expire_trials_without_payment,
)


class TestExpireTrialsService:
    def test_returns_count_of_expired_trials(
        self,
        abandoned_trial_subscription: Subscription,
    ) -> None:
        service = ExpireTrialsService()
        count = service()
        assert count == 1

    def test_expires_abandoned_trials(
        self,
        abandoned_trial_subscription: Subscription,
    ) -> None:
        service = ExpireTrialsService()
        service()
        abandoned_trial_subscription.refresh_from_db()
        assert abandoned_trial_subscription.status == SubscriptionStatus.EXPIRED

    def test_returns_zero_if_no_abandoned_trials(self) -> None:
        service = ExpireTrialsService()
        assert service() == 0

    def test_does_not_expire_trial_with_pending_tariff(
        self,
        abandoned_trial_subscription: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        """Trial with pending_tariff is not abandoned — should not be expired."""
        abandoned_trial_subscription.pending_tariff = paid_tariff
        abandoned_trial_subscription.save(update_fields=['pending_tariff'])
        service = ExpireTrialsService()
        count = service()
        assert count == 0
        abandoned_trial_subscription.refresh_from_db()
        assert abandoned_trial_subscription.status == SubscriptionStatus.TRIAL

    def test_does_not_expire_trial_with_future_trial_end(
        self,
        abandoned_trial_subscription: Subscription,
    ) -> None:
        """Trial that hasn't ended yet is not picked up."""
        abandoned_trial_subscription.trial_ended_at = timezone.now() + timedelta(hours=1)
        abandoned_trial_subscription.save(update_fields=['trial_ended_at'])
        service = ExpireTrialsService()
        count = service()
        assert count == 0


class TestExpirePastDueService:
    def test_returns_count_of_expired_subscriptions(
        self,
        past_due_subscription_for_expiry: Subscription,
    ) -> None:
        service = ExpirePastDueService()
        count = service()
        assert count == 1

    def test_expires_past_due_subscriptions(
        self,
        past_due_subscription_for_expiry: Subscription,
    ) -> None:
        service = ExpirePastDueService()
        service()
        past_due_subscription_for_expiry.refresh_from_db()
        assert past_due_subscription_for_expiry.status == SubscriptionStatus.EXPIRED

    def test_returns_zero_if_no_subscriptions(self) -> None:
        service = ExpirePastDueService()
        assert service() == 0

    def test_does_not_expire_past_due_within_grace_period(
        self,
        past_due_subscription_for_expiry: Subscription,
    ) -> None:
        """PAST_DUE subscription still within grace period is not expired yet."""
        from apps.subscriptions.constants import GRACE_PERIOD_DAYS

        past_due_subscription_for_expiry.current_period_end = timezone.now() - timedelta(days=GRACE_PERIOD_DAYS - 1)
        past_due_subscription_for_expiry.save(update_fields=['current_period_end'])
        service = ExpirePastDueService()
        count = service()
        assert count == 0
        past_due_subscription_for_expiry.refresh_from_db()
        assert past_due_subscription_for_expiry.status == SubscriptionStatus.PAST_DUE

    def test_does_not_expire_active_subscription(
        self,
        past_due_subscription_for_expiry: Subscription,
    ) -> None:
        past_due_subscription_for_expiry.status = SubscriptionStatus.ACTIVE
        past_due_subscription_for_expiry.save(update_fields=['status'])
        service = ExpirePastDueService()
        count = service()
        assert count == 0


class TestExpireCancelledService:
    def test_returns_count_of_expired_subscriptions(
        self,
        cancelled_subscription_ready_to_expire: Subscription,
    ) -> None:
        service = ExpireCancelledService()
        count = service()
        assert count == 1

    def test_expires_cancelled_subscriptions(
        self,
        cancelled_subscription_ready_to_expire: Subscription,
    ) -> None:
        service = ExpireCancelledService()
        service()
        cancelled_subscription_ready_to_expire.refresh_from_db()
        assert cancelled_subscription_ready_to_expire.status == SubscriptionStatus.EXPIRED

    def test_returns_zero_if_no_subscriptions(self) -> None:
        service = ExpireCancelledService()
        assert service() == 0

    def test_does_not_expire_subscription_with_future_period_end(
        self,
        cancelled_subscription_ready_to_expire: Subscription,
    ) -> None:
        cancelled_subscription_ready_to_expire.current_period_end = timezone.now() + timedelta(hours=1)
        cancelled_subscription_ready_to_expire.save(update_fields=['current_period_end'])
        service = ExpireCancelledService()
        count = service()
        assert count == 0

    def test_does_not_expire_subscription_with_auto_renew(
        self,
        cancelled_subscription_ready_to_expire: Subscription,
    ) -> None:
        """ACTIVE subscription with auto_renew=True should be handled by renewals, not expire."""
        cancelled_subscription_ready_to_expire.auto_renew = True
        cancelled_subscription_ready_to_expire.save(update_fields=['auto_renew'])
        service = ExpireCancelledService()
        count = service()
        assert count == 0


class TestExpireTrialsWithoutPaymentTask:
    def test_task_returns_formatted_string(
        self,
        abandoned_trial_subscription: Subscription,
    ) -> None:
        result = expire_trials_without_payment()
        assert 'Expired 1 abandoned trials.' in result

    def test_task_calls_service(self, mocker: MockFixture) -> None:
        mock_call = mocker.patch.object(ExpireTrialsService, '__call__', return_value=0)
        result = expire_trials_without_payment()
        mock_call.assert_called_once()
        assert 'Expired 0 abandoned trials.' in result


class TestExpirePastDueSubscriptionsTask:
    def test_task_returns_formatted_string(
        self,
        past_due_subscription_for_expiry: Subscription,
    ) -> None:
        result = expire_past_due_subscriptions()
        assert 'Expired 1 past-due subscriptions.' in result

    def test_task_calls_service(self, mocker: MockFixture) -> None:
        mock_call = mocker.patch.object(ExpirePastDueService, '__call__', return_value=0)
        result = expire_past_due_subscriptions()
        mock_call.assert_called_once()
        assert 'Expired 0 past-due subscriptions.' in result


class TestExpireCancelledSubscriptionsTask:
    def test_task_returns_formatted_string(
        self,
        cancelled_subscription_ready_to_expire: Subscription,
    ) -> None:
        result = expire_cancelled_subscriptions()
        assert 'Expired 1 cancelled subscriptions.' in result

    def test_task_calls_service(self, mocker: MockFixture) -> None:
        mock_call = mocker.patch.object(ExpireCancelledService, '__call__', return_value=0)
        result = expire_cancelled_subscriptions()
        mock_call.assert_called_once()
        assert 'Expired 0 cancelled subscriptions.' in result
