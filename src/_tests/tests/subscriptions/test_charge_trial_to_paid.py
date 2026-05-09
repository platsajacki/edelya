import pytest
from pytest_mock import MockFixture, MockType

from datetime import timedelta

from django.utils import timezone

from apps.subscriptions.exceptions import PaymentPendingRecurringError
from apps.subscriptions.models import Subscription, Tariff
from apps.subscriptions.models.model_enums import PaymentStatus, PaymentType, SubscriptionStatus
from apps.subscriptions.models.payments import Payment
from apps.subscriptions.services.webhook_handler import WebhookAction
from apps.subscriptions.tasks.trials import ChargeTrialToPaidService, process_trial_to_paid


class TestCreatePayment:
    def test_creates_payment_with_correct_fields(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        service = ChargeTrialToPaidService(timezone.now())
        payment = service.create_payment(trial_subscription_ready_to_charge, paid_tariff)
        assert payment.subscription == trial_subscription_ready_to_charge
        assert payment.user == trial_subscription_ready_to_charge.user
        assert payment.amount == paid_tariff.price
        assert payment.payment_type == PaymentType.RECURRING
        assert payment.status == PaymentStatus.PENDING
        assert payment.metadata['action'] == WebhookAction.FIRST_PAYMENT
        assert payment.metadata['tariff_id'] == str(paid_tariff.id)

    def test_idempotence_key_is_unique_uuid(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        service = ChargeTrialToPaidService(timezone.now())
        p1 = service.create_payment(trial_subscription_ready_to_charge, paid_tariff)
        p2 = service.create_payment(trial_subscription_ready_to_charge, paid_tariff)
        assert str(p1.idempotence_key) != str(p2.idempotence_key)


class TestTryChargePayment:
    def test_calls_yookassa_with_correct_params(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
        mocker: MockFixture,
        yookassa_succeeded_response: MockType,
    ) -> None:
        mock_create = mocker.patch(
            'apps.subscriptions.tasks.trials.yookassa_service.create_payment',
            return_value=yookassa_succeeded_response,
        )
        service = ChargeTrialToPaidService(timezone.now())
        payment = service.create_payment(trial_subscription_ready_to_charge, paid_tariff)
        service.try_charge_payment(payment, paid_tariff, trial_subscription_ready_to_charge)
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs['amount'] == paid_tariff.price
        assert trial_subscription_ready_to_charge.payment_method is not None
        assert call_kwargs['payment_method_id'] == (
            trial_subscription_ready_to_charge.payment_method.yookassa_payment_method_id
        )
        assert call_kwargs['capture'] is True
        assert paid_tariff.name in call_kwargs['description']

    def test_raises_payment_pending_recurring_error_on_yookassa_exception(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        mock_yookassa_payment_create.side_effect = Exception('network error')
        service = ChargeTrialToPaidService(timezone.now())
        payment = service.create_payment(trial_subscription_ready_to_charge, paid_tariff)
        with pytest.raises(PaymentPendingRecurringError):
            service.try_charge_payment(payment, paid_tariff, trial_subscription_ready_to_charge)


class TestProcessPayment:
    def test_sets_payment_succeeded_and_paid_at(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        service = ChargeTrialToPaidService(timezone.now())
        payment = service.create_payment(trial_subscription_ready_to_charge, paid_tariff)
        service.process_payment(payment, paid_tariff, trial_subscription_ready_to_charge, succeeded=True)
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.SUCCEEDED
        assert payment.paid_at is not None

    def test_sets_subscription_active_with_correct_tariff(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        service = ChargeTrialToPaidService(timezone.now())
        payment = service.create_payment(trial_subscription_ready_to_charge, paid_tariff)
        service.process_payment(payment, paid_tariff, trial_subscription_ready_to_charge, succeeded=True)
        trial_subscription_ready_to_charge.refresh_from_db()
        assert trial_subscription_ready_to_charge.status == SubscriptionStatus.ACTIVE
        assert trial_subscription_ready_to_charge.tariff == paid_tariff
        assert trial_subscription_ready_to_charge.pending_tariff is None

    def test_sets_trial_ended_at_if_none(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        trial_subscription_ready_to_charge.trial_ended_at = None
        trial_subscription_ready_to_charge.save(update_fields=['trial_ended_at'])
        before = timezone.now()
        service = ChargeTrialToPaidService(timezone.now())
        payment = service.create_payment(trial_subscription_ready_to_charge, paid_tariff)
        service.process_payment(payment, paid_tariff, trial_subscription_ready_to_charge, succeeded=True)
        after = timezone.now()
        trial_subscription_ready_to_charge.refresh_from_db()
        assert trial_subscription_ready_to_charge.trial_ended_at is not None
        assert before <= trial_subscription_ready_to_charge.trial_ended_at <= after

    def test_keeps_existing_trial_ended_at(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        original = trial_subscription_ready_to_charge.trial_ended_at
        service = ChargeTrialToPaidService(timezone.now())
        payment = service.create_payment(trial_subscription_ready_to_charge, paid_tariff)
        service.process_payment(payment, paid_tariff, trial_subscription_ready_to_charge, succeeded=True)
        trial_subscription_ready_to_charge.refresh_from_db()
        assert trial_subscription_ready_to_charge.trial_ended_at == original

    def test_sets_current_period_start_to_trial_ended_at(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        trial_ended_at = trial_subscription_ready_to_charge.trial_ended_at
        service = ChargeTrialToPaidService(timezone.now())
        payment = service.create_payment(trial_subscription_ready_to_charge, paid_tariff)
        service.process_payment(payment, paid_tariff, trial_subscription_ready_to_charge, succeeded=True)
        trial_subscription_ready_to_charge.refresh_from_db()
        assert trial_subscription_ready_to_charge.current_period_start == trial_ended_at

    def test_sets_current_period_end_via_get_next_period_end(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        assert trial_subscription_ready_to_charge.trial_ended_at is not None
        expected = paid_tariff.get_next_period_end(trial_subscription_ready_to_charge.trial_ended_at)
        service = ChargeTrialToPaidService(timezone.now())
        payment = service.create_payment(trial_subscription_ready_to_charge, paid_tariff)
        service.process_payment(payment, paid_tariff, trial_subscription_ready_to_charge, succeeded=True)
        trial_subscription_ready_to_charge.refresh_from_db()
        assert trial_subscription_ready_to_charge.current_period_end == expected

    def test_sets_payment_canceled_with_reason(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        service = ChargeTrialToPaidService(timezone.now())
        payment = service.create_payment(trial_subscription_ready_to_charge, paid_tariff)
        service.process_payment(
            payment,
            paid_tariff,
            trial_subscription_ready_to_charge,
            succeeded=False,
            cancellation_reason='card_expired',
        )
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.CANCELED
        assert payment.cancellation_reason == 'card_expired'

    def test_sets_subscription_past_due(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        service = ChargeTrialToPaidService(timezone.now())
        payment = service.create_payment(trial_subscription_ready_to_charge, paid_tariff)
        service.process_payment(
            payment,
            paid_tariff,
            trial_subscription_ready_to_charge,
            succeeded=False,
            cancellation_reason='insufficient_funds',
        )
        trial_subscription_ready_to_charge.refresh_from_db()
        assert trial_subscription_ready_to_charge.status == SubscriptionStatus.PAST_DUE

    def test_applies_pending_tariff_on_cancel(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        """Tariff is applied even when payment fails."""
        service = ChargeTrialToPaidService(timezone.now())
        payment = service.create_payment(trial_subscription_ready_to_charge, paid_tariff)
        service.process_payment(
            payment,
            paid_tariff,
            trial_subscription_ready_to_charge,
            succeeded=False,
            cancellation_reason='card_expired',
        )
        trial_subscription_ready_to_charge.refresh_from_db()
        assert trial_subscription_ready_to_charge.tariff == paid_tariff

    def test_clears_pending_tariff_on_cancel(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        service = ChargeTrialToPaidService(timezone.now())
        payment = service.create_payment(trial_subscription_ready_to_charge, paid_tariff)
        service.process_payment(
            payment,
            paid_tariff,
            trial_subscription_ready_to_charge,
            succeeded=False,
            cancellation_reason='card_expired',
        )
        trial_subscription_ready_to_charge.refresh_from_db()
        assert trial_subscription_ready_to_charge.pending_tariff is None

    def test_sets_period_on_cancel(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        """current_period_start/end are calculated the same way on cancel."""
        assert trial_subscription_ready_to_charge.trial_ended_at is not None
        trial_ended_at = trial_subscription_ready_to_charge.trial_ended_at
        expected_end = paid_tariff.get_next_period_end(trial_ended_at)
        service = ChargeTrialToPaidService(timezone.now())
        payment = service.create_payment(trial_subscription_ready_to_charge, paid_tariff)
        service.process_payment(
            payment,
            paid_tariff,
            trial_subscription_ready_to_charge,
            succeeded=False,
            cancellation_reason='card_expired',
        )
        trial_subscription_ready_to_charge.refresh_from_db()
        assert trial_subscription_ready_to_charge.current_period_start == trial_ended_at
        assert trial_subscription_ready_to_charge.current_period_end == expected_end

    def test_atomic_rollback_if_subscription_save_fails(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
        mocker: MockFixture,
    ) -> None:
        service = ChargeTrialToPaidService(timezone.now())
        payment = service.create_payment(trial_subscription_ready_to_charge, paid_tariff)
        mocker.patch.object(trial_subscription_ready_to_charge, 'save', side_effect=Exception('db error'))
        with pytest.raises(Exception, match='db error'):
            service.process_payment(
                payment,
                paid_tariff,
                trial_subscription_ready_to_charge,
                succeeded=False,
                cancellation_reason='card_expired',
            )
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.PENDING


class TestProcessSubscription:
    def test_happy_path_yookassa_succeeded(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
        yookassa_succeeded_response: MockType,
    ) -> None:
        mock_yookassa_payment_create.return_value = yookassa_succeeded_response
        service = ChargeTrialToPaidService(timezone.now())
        service.process_subscription(trial_subscription_ready_to_charge, paid_tariff)
        trial_subscription_ready_to_charge.refresh_from_db()
        assert trial_subscription_ready_to_charge.status == SubscriptionStatus.ACTIVE
        assert trial_subscription_ready_to_charge.tariff == paid_tariff

    def test_skips_if_pending_recurring_payment_exists(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
        pending_recurring_payment_for_trial: Payment,
    ) -> None:
        """check_pending_recurring_payment raises PaymentPendingRecurringError — no new payment created."""
        service = ChargeTrialToPaidService(timezone.now() - timedelta(minutes=10))
        initial_count = Payment.objects.filter(subscription=trial_subscription_ready_to_charge).count()
        with pytest.raises(PaymentPendingRecurringError):
            service.process_subscription(trial_subscription_ready_to_charge, paid_tariff)
        assert Payment.objects.filter(subscription=trial_subscription_ready_to_charge).count() == initial_count

    def test_cancels_payment_on_yookassa_failure_exception(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        mock_yookassa_payment_create.side_effect = Exception('gateway timeout')
        service = ChargeTrialToPaidService(timezone.now())
        service.process_subscription(trial_subscription_ready_to_charge, paid_tariff)
        payment = Payment.objects.filter(
            subscription=trial_subscription_ready_to_charge,
            payment_type=PaymentType.RECURRING,
        ).latest('created_at')
        assert payment.status == PaymentStatus.CANCELED
        trial_subscription_ready_to_charge.refresh_from_db()
        assert trial_subscription_ready_to_charge.status == SubscriptionStatus.PAST_DUE
        assert trial_subscription_ready_to_charge.tariff == paid_tariff

    def test_cancels_payment_on_yookassa_non_succeeded_status(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
        yookassa_canceled_response: MockType,
    ) -> None:
        mock_yookassa_payment_create.return_value = yookassa_canceled_response
        service = ChargeTrialToPaidService(timezone.now())
        service.process_subscription(trial_subscription_ready_to_charge, paid_tariff)
        payment = Payment.objects.filter(
            subscription=trial_subscription_ready_to_charge,
            payment_type=PaymentType.RECURRING,
        ).latest('created_at')
        assert payment.status == PaymentStatus.CANCELED
        trial_subscription_ready_to_charge.refresh_from_db()
        assert trial_subscription_ready_to_charge.status == SubscriptionStatus.PAST_DUE
        assert trial_subscription_ready_to_charge.tariff == paid_tariff


class TestAct:
    def test_returns_zero_if_no_subscriptions(self) -> None:
        future = timezone.now() - timedelta(days=1)  # no subscription has trial_ended_at in the past
        service = ChargeTrialToPaidService(future)
        assert service() == 0

    def test_returns_count_of_processed_subscriptions(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
        yookassa_succeeded_response: MockType,
    ) -> None:
        mock_yookassa_payment_create.return_value = yookassa_succeeded_response
        service = ChargeTrialToPaidService(timezone.now())
        count = service()
        assert count == 1

    def test_skips_subscription_without_pending_tariff(
        self,
        trial_subscription_ready_to_charge: Subscription,
    ) -> None:
        """pending_tariff=None raises SubscriptionDoesHavePendingTariffError → warning, count stays 0."""
        trial_subscription_ready_to_charge.pending_tariff = None
        trial_subscription_ready_to_charge.save(update_fields=['pending_tariff'])
        service = ChargeTrialToPaidService(timezone.now())
        count = service()
        assert count == 0

    def test_continues_on_generic_exception(
        self,
        trial_subscription_ready_to_charge: Subscription,
        paid_tariff: Tariff,
        mocker: MockFixture,
    ) -> None:
        """One subscription raises Exception → logged as error, others are still processed."""
        mocker.patch.object(
            ChargeTrialToPaidService,
            'process_subscription',
            side_effect=Exception('unexpected'),
        )
        service = ChargeTrialToPaidService(timezone.now())
        count = service()
        assert count == 0  # exception was swallowed

    def test_subscription_not_in_window_not_processed(
        self,
        trial_subscription_ready_to_charge: Subscription,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        """Subscription with trial_ended_at in the future is not in queryset."""
        future_trial_end = timezone.now() + timedelta(hours=1)
        trial_subscription_ready_to_charge.trial_ended_at = future_trial_end
        trial_subscription_ready_to_charge.save(update_fields=['trial_ended_at'])
        # service window ends now — future trial not included
        service = ChargeTrialToPaidService(timezone.now())
        count = service()
        assert count == 0
        mock_yookassa_payment_create.assert_not_called()


class TestProcessTrialToPaidTask:
    def test_task_returns_formatted_string(
        self,
        trial_subscription_ready_to_charge: Subscription,
        mock_yookassa_payment_create: MockType,
        yookassa_succeeded_response: MockType,
    ) -> None:
        mock_yookassa_payment_create.return_value = yookassa_succeeded_response
        result = process_trial_to_paid()
        assert result == 'Charged 1 trials to paid.'

    def test_task_passes_now_plus_5min_to_service(self, mocker: MockFixture) -> None:
        """Task should pass now + 5 minutes to ChargeTrialToPaidService."""
        mock_call = mocker.patch.object(ChargeTrialToPaidService, '__call__', return_value=0)
        mock_init = mocker.spy(ChargeTrialToPaidService, '__init__')
        before = timezone.now()
        process_trial_to_paid()
        after = timezone.now()
        passed_dt = mock_init.call_args[0][1]  # first positional arg after self
        assert before + timedelta(minutes=4, seconds=59) <= passed_dt <= after + timedelta(minutes=5, seconds=1)
        mock_call.assert_called_once()
