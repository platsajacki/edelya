import pytest
from pytest_mock import MockFixture, MockType

from django.utils import timezone

from apps.subscriptions.exceptions import PaymentPendingRecurringError
from apps.subscriptions.models import Subscription, Tariff
from apps.subscriptions.models.model_enums import PaymentStatus, PaymentType, SubscriptionStatus
from apps.subscriptions.models.payments import Payment
from apps.subscriptions.services.webhook_handler import WebhookAction
from apps.subscriptions.tasks.past_due import ChargePastDueService, process_past_due_charge


class TestCreatePayment:
    def test_creates_payment_with_correct_fields(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        service = ChargePastDueService()
        payment = service.create_payment(
            past_due_subscription_ready_for_retry, paid_tariff, action=WebhookAction.RECURRING
        )
        assert payment.subscription == past_due_subscription_ready_for_retry
        assert payment.user == past_due_subscription_ready_for_retry.user
        assert payment.amount == paid_tariff.price
        assert payment.payment_type == PaymentType.RECURRING
        assert payment.status == PaymentStatus.PENDING
        assert payment.payment_method == past_due_subscription_ready_for_retry.payment_method
        assert payment.metadata['action'] == WebhookAction.RECURRING
        assert payment.metadata['tariff_id'] == str(paid_tariff.id)

    def test_idempotence_key_is_unique_uuid(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        service = ChargePastDueService()
        p1 = service.create_payment(past_due_subscription_ready_for_retry, paid_tariff, action=WebhookAction.RECURRING)
        p2 = service.create_payment(past_due_subscription_ready_for_retry, paid_tariff, action=WebhookAction.RECURRING)
        assert str(p1.idempotence_key) != str(p2.idempotence_key)


class TestTryChargePayment:
    def test_calls_yookassa_with_correct_params(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        paid_tariff: Tariff,
        mocker: MockFixture,
        yookassa_succeeded_response: MockType,
    ) -> None:
        mock_create = mocker.patch(
            'apps.subscriptions.tasks.base.yookassa_service.create_payment',
            return_value=yookassa_succeeded_response,
        )
        service = ChargePastDueService()
        payment = service.create_payment(
            past_due_subscription_ready_for_retry, paid_tariff, action=WebhookAction.RECURRING
        )
        service.try_charge_payment(
            payment,
            paid_tariff,
            past_due_subscription_ready_for_retry,
            description=f'Повторное списание подписки "{paid_tariff.name}"',
        )
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs['amount'] == paid_tariff.price
        assert past_due_subscription_ready_for_retry.payment_method is not None
        assert call_kwargs['payment_method_id'] == (
            past_due_subscription_ready_for_retry.payment_method.yookassa_payment_method_id
        )
        assert call_kwargs['capture'] is True
        assert paid_tariff.name in call_kwargs['description']

    def test_raises_payment_pending_recurring_error_on_yookassa_exception(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        paid_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        mock_yookassa_payment_create.side_effect = Exception('network error')
        service = ChargePastDueService()
        payment = service.create_payment(
            past_due_subscription_ready_for_retry, paid_tariff, action=WebhookAction.RECURRING
        )
        with pytest.raises(PaymentPendingRecurringError):
            service.try_charge_payment(
                payment,
                paid_tariff,
                past_due_subscription_ready_for_retry,
                description=f'Повторное списание подписки "{paid_tariff.name}"',
            )


class TestProcessPayment:
    def test_sets_payment_succeeded_and_paid_at(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        service = ChargePastDueService()
        payment = service.create_payment(
            past_due_subscription_ready_for_retry, paid_tariff, action=WebhookAction.RECURRING
        )
        period_start = past_due_subscription_ready_for_retry.current_period_end
        assert period_start is not None
        service.process_payment(
            payment,
            paid_tariff,
            past_due_subscription_ready_for_retry,
            succeeded=True,
            period_start=period_start,
            failed_status=SubscriptionStatus.EXPIRED,
        )
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.SUCCEEDED
        assert payment.paid_at is not None

    def test_sets_subscription_active_on_success(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        service = ChargePastDueService()
        payment = service.create_payment(
            past_due_subscription_ready_for_retry, paid_tariff, action=WebhookAction.RECURRING
        )
        period_start = past_due_subscription_ready_for_retry.current_period_end
        assert period_start is not None
        service.process_payment(
            payment,
            paid_tariff,
            past_due_subscription_ready_for_retry,
            succeeded=True,
            period_start=period_start,
            failed_status=SubscriptionStatus.EXPIRED,
        )
        past_due_subscription_ready_for_retry.refresh_from_db()
        assert past_due_subscription_ready_for_retry.status == SubscriptionStatus.ACTIVE

    def test_keeps_current_period_start_on_success(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        period_start = past_due_subscription_ready_for_retry.current_period_start
        assert period_start is not None
        service = ChargePastDueService()
        payment = service.create_payment(
            past_due_subscription_ready_for_retry, paid_tariff, action=WebhookAction.RECURRING
        )
        service.process_payment(
            payment,
            paid_tariff,
            past_due_subscription_ready_for_retry,
            succeeded=True,
            period_start=period_start,
            failed_status=SubscriptionStatus.EXPIRED,
        )
        past_due_subscription_ready_for_retry.refresh_from_db()
        assert past_due_subscription_ready_for_retry.current_period_start == period_start

    def test_keeps_current_period_end_on_success(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        period_end = past_due_subscription_ready_for_retry.current_period_end
        assert period_end is not None
        service = ChargePastDueService()
        payment = service.create_payment(
            past_due_subscription_ready_for_retry, paid_tariff, action=WebhookAction.RECURRING
        )
        service.process_payment(
            payment,
            paid_tariff,
            past_due_subscription_ready_for_retry,
            succeeded=True,
            period_start=period_end,
            failed_status=SubscriptionStatus.EXPIRED,
        )
        past_due_subscription_ready_for_retry.refresh_from_db()
        assert past_due_subscription_ready_for_retry.current_period_end == period_end

    def test_sets_payment_canceled_with_reason(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        service = ChargePastDueService()
        payment = service.create_payment(
            past_due_subscription_ready_for_retry, paid_tariff, action=WebhookAction.RECURRING
        )
        period_start = past_due_subscription_ready_for_retry.current_period_end
        assert period_start is not None
        service.process_payment(
            payment,
            paid_tariff,
            past_due_subscription_ready_for_retry,
            succeeded=False,
            cancellation_reason='card_expired',
            period_start=period_start,
            failed_status=SubscriptionStatus.EXPIRED,
        )
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.CANCELED
        assert payment.cancellation_reason == 'card_expired'
        assert payment.payment_method == past_due_subscription_ready_for_retry.payment_method

    def test_sets_subscription_expired_on_failure(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        """Failed retry moves subscription to EXPIRED, not PAST_DUE."""
        service = ChargePastDueService()
        payment = service.create_payment(
            past_due_subscription_ready_for_retry, paid_tariff, action=WebhookAction.RECURRING
        )
        period_start = past_due_subscription_ready_for_retry.current_period_end
        assert period_start is not None
        service.process_payment(
            payment,
            paid_tariff,
            past_due_subscription_ready_for_retry,
            succeeded=False,
            cancellation_reason='insufficient_funds',
            period_start=period_start,
            failed_status=SubscriptionStatus.EXPIRED,
        )
        payment.refresh_from_db()
        past_due_subscription_ready_for_retry.refresh_from_db()
        assert payment.payment_method == past_due_subscription_ready_for_retry.payment_method
        assert past_due_subscription_ready_for_retry.status == SubscriptionStatus.EXPIRED

    def test_atomic_rollback_if_subscription_save_fails(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        paid_tariff: Tariff,
        mocker: MockFixture,
    ) -> None:
        service = ChargePastDueService()
        payment = service.create_payment(
            past_due_subscription_ready_for_retry, paid_tariff, action=WebhookAction.RECURRING
        )
        period_start = past_due_subscription_ready_for_retry.current_period_end
        assert period_start is not None
        mocker.patch.object(past_due_subscription_ready_for_retry, 'save', side_effect=Exception('db error'))
        with pytest.raises(Exception, match='db error'):
            service.process_payment(
                payment,
                paid_tariff,
                past_due_subscription_ready_for_retry,
                succeeded=True,
                period_start=period_start,
                failed_status=SubscriptionStatus.EXPIRED,
            )
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.PENDING


class TestProcessSubscription:
    def test_happy_path_yookassa_succeeded(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        paid_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
        yookassa_succeeded_response: MockType,
    ) -> None:
        mock_yookassa_payment_create.return_value = yookassa_succeeded_response
        service = ChargePastDueService()
        service.process_subscription(past_due_subscription_ready_for_retry, paid_tariff)
        past_due_subscription_ready_for_retry.refresh_from_db()
        assert past_due_subscription_ready_for_retry.status == SubscriptionStatus.ACTIVE
        assert past_due_subscription_ready_for_retry.tariff == paid_tariff

    def test_skips_if_pending_recurring_payment_exists(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        paid_tariff: Tariff,
        pending_recurring_payment_for_past_due: Payment,
    ) -> None:
        """check_pending_recurring_payment raises PaymentPendingRecurringError — no new payment created."""
        service = ChargePastDueService()
        initial_count = Payment.objects.filter(subscription=past_due_subscription_ready_for_retry).count()
        with pytest.raises(PaymentPendingRecurringError):
            service.process_subscription(past_due_subscription_ready_for_retry, paid_tariff)
        assert Payment.objects.filter(subscription=past_due_subscription_ready_for_retry).count() == initial_count

    def test_expires_subscription_on_yookassa_failure_exception(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        paid_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        mock_yookassa_payment_create.side_effect = Exception('gateway timeout')
        service = ChargePastDueService()
        service.process_subscription(past_due_subscription_ready_for_retry, paid_tariff)
        payment = Payment.objects.filter(
            subscription=past_due_subscription_ready_for_retry,
            payment_type=PaymentType.RECURRING,
        ).latest('created_at')
        assert payment.status == PaymentStatus.CANCELED
        past_due_subscription_ready_for_retry.refresh_from_db()
        assert past_due_subscription_ready_for_retry.status == SubscriptionStatus.EXPIRED

    def test_expires_subscription_on_yookassa_non_succeeded_status(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        paid_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
        yookassa_canceled_response: MockType,
    ) -> None:
        mock_yookassa_payment_create.return_value = yookassa_canceled_response
        service = ChargePastDueService()
        service.process_subscription(past_due_subscription_ready_for_retry, paid_tariff)
        payment = Payment.objects.filter(
            subscription=past_due_subscription_ready_for_retry,
            payment_type=PaymentType.RECURRING,
        ).latest('created_at')
        assert payment.status == PaymentStatus.CANCELED
        past_due_subscription_ready_for_retry.refresh_from_db()
        assert past_due_subscription_ready_for_retry.status == SubscriptionStatus.EXPIRED


class TestAct:
    def test_returns_zero_if_no_subscriptions(self) -> None:
        service = ChargePastDueService()
        assert service() == 0

    def test_returns_count_of_processed_subscriptions(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        paid_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
        yookassa_succeeded_response: MockType,
    ) -> None:
        mock_yookassa_payment_create.return_value = yookassa_succeeded_response
        service = ChargePastDueService()
        count = service()
        assert count == 1

    def test_continues_on_generic_exception(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        paid_tariff: Tariff,
        mocker: MockFixture,
    ) -> None:
        mocker.patch.object(
            ChargePastDueService,
            'process_subscription',
            side_effect=Exception('unexpected'),
        )
        service = ChargePastDueService()
        count = service()
        assert count == 0

    def test_subscription_not_in_grace_period_window_not_processed(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        """Subscription with current_period_start too recent is not in queryset."""
        past_due_subscription_ready_for_retry.current_period_start = timezone.now()
        past_due_subscription_ready_for_retry.save(update_fields=['current_period_start'])
        service = ChargePastDueService()
        count = service()
        assert count == 0
        mock_yookassa_payment_create.assert_not_called()

    def test_uses_pending_tariff_when_present(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        paid_tariff: Tariff,
        upgrade_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
        yookassa_succeeded_response: MockType,
    ) -> None:
        """When pending_tariff is set, act() uses it instead of current tariff."""
        past_due_subscription_ready_for_retry.pending_tariff = upgrade_tariff
        past_due_subscription_ready_for_retry.save(update_fields=['pending_tariff'])
        mock_yookassa_payment_create.return_value = yookassa_succeeded_response
        service = ChargePastDueService()
        service()
        past_due_subscription_ready_for_retry.refresh_from_db()
        assert past_due_subscription_ready_for_retry.tariff == upgrade_tariff


class TestProcessPastDueChargeTask:
    def test_task_returns_formatted_string(
        self,
        past_due_subscription_ready_for_retry: Subscription,
        mock_yookassa_payment_create: MockType,
        yookassa_succeeded_response: MockType,
    ) -> None:
        mock_yookassa_payment_create.return_value = yookassa_succeeded_response
        result = process_past_due_charge()
        assert 'Charged 1 past-due subscriptions.' in result

    def test_task_calls_service(self, mocker: MockFixture) -> None:
        mock_call = mocker.patch.object(ChargePastDueService, '__call__', return_value=0)
        result = process_past_due_charge()
        mock_call.assert_called_once()
        assert 'Charged 0 past-due subscriptions.' in result
