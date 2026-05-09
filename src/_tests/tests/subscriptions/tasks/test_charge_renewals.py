import pytest
from pytest_mock import MockFixture, MockType

from datetime import timedelta

from django.utils import timezone

from apps.subscriptions.exceptions import PaymentPendingRecurringError
from apps.subscriptions.models import Subscription, Tariff
from apps.subscriptions.models.model_enums import PaymentStatus, PaymentType, SubscriptionStatus
from apps.subscriptions.models.payments import Payment
from apps.subscriptions.services.webhook_handler import WebhookAction
from apps.subscriptions.tasks.renewals import ChargeRenewalService, process_subscription_renewals


class TestCreatePayment:
    def test_creates_payment_with_correct_fields(
        self,
        active_subscription_ready_to_renew: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        service = ChargeRenewalService()
        payment = service.create_payment(
            active_subscription_ready_to_renew, paid_tariff, action=WebhookAction.RECURRING
        )
        assert payment.subscription == active_subscription_ready_to_renew
        assert payment.user == active_subscription_ready_to_renew.user
        assert payment.amount == paid_tariff.price
        assert payment.payment_type == PaymentType.RECURRING
        assert payment.status == PaymentStatus.PENDING
        assert payment.metadata['action'] == WebhookAction.RECURRING
        assert payment.metadata['tariff_id'] == str(paid_tariff.id)

    def test_idempotence_key_is_unique_uuid(
        self,
        active_subscription_ready_to_renew: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        service = ChargeRenewalService()
        p1 = service.create_payment(active_subscription_ready_to_renew, paid_tariff, action=WebhookAction.RECURRING)
        p2 = service.create_payment(active_subscription_ready_to_renew, paid_tariff, action=WebhookAction.RECURRING)
        assert str(p1.idempotence_key) != str(p2.idempotence_key)


class TestTryChargePayment:
    def test_calls_yookassa_with_correct_params(
        self,
        active_subscription_ready_to_renew: Subscription,
        paid_tariff: Tariff,
        mocker: MockFixture,
        yookassa_succeeded_response: MockType,
    ) -> None:
        mock_create = mocker.patch(
            'apps.subscriptions.tasks.base.yookassa_service.create_payment',
            return_value=yookassa_succeeded_response,
        )
        service = ChargeRenewalService()
        payment = service.create_payment(
            active_subscription_ready_to_renew, paid_tariff, action=WebhookAction.RECURRING
        )
        service.try_charge_payment(
            payment,
            paid_tariff,
            active_subscription_ready_to_renew,
            description=f'Продление подписки "{paid_tariff.name}"',
        )
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs['amount'] == paid_tariff.price
        assert active_subscription_ready_to_renew.payment_method is not None
        assert call_kwargs['payment_method_id'] == (
            active_subscription_ready_to_renew.payment_method.yookassa_payment_method_id
        )
        assert call_kwargs['capture'] is True
        assert paid_tariff.name in call_kwargs['description']

    def test_raises_payment_pending_recurring_error_on_yookassa_exception(
        self,
        active_subscription_ready_to_renew: Subscription,
        paid_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        mock_yookassa_payment_create.side_effect = Exception('network error')
        service = ChargeRenewalService()
        payment = service.create_payment(
            active_subscription_ready_to_renew, paid_tariff, action=WebhookAction.RECURRING
        )
        with pytest.raises(PaymentPendingRecurringError):
            service.try_charge_payment(
                payment,
                paid_tariff,
                active_subscription_ready_to_renew,
                description=f'Продление подписки "{paid_tariff.name}"',
            )


class TestProcessPayment:
    def test_sets_payment_succeeded_and_paid_at(
        self,
        active_subscription_ready_to_renew: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        service = ChargeRenewalService()
        payment = service.create_payment(
            active_subscription_ready_to_renew, paid_tariff, action=WebhookAction.RECURRING
        )
        period_start = active_subscription_ready_to_renew.current_period_end
        assert period_start is not None
        service.process_payment(
            payment,
            paid_tariff,
            active_subscription_ready_to_renew,
            succeeded=True,
            period_start=period_start,
            failed_status=SubscriptionStatus.PAST_DUE,
        )
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.SUCCEEDED
        assert payment.paid_at is not None

    def test_sets_subscription_active_with_correct_tariff(
        self,
        active_subscription_ready_to_renew: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        service = ChargeRenewalService()
        payment = service.create_payment(
            active_subscription_ready_to_renew, paid_tariff, action=WebhookAction.RECURRING
        )
        period_start = active_subscription_ready_to_renew.current_period_end
        assert period_start is not None
        service.process_payment(
            payment,
            paid_tariff,
            active_subscription_ready_to_renew,
            succeeded=True,
            period_start=period_start,
            failed_status=SubscriptionStatus.PAST_DUE,
        )
        active_subscription_ready_to_renew.refresh_from_db()
        assert active_subscription_ready_to_renew.status == SubscriptionStatus.ACTIVE
        assert active_subscription_ready_to_renew.tariff == paid_tariff
        assert active_subscription_ready_to_renew.pending_tariff is None

    def test_sets_current_period_start_to_old_period_end(
        self,
        active_subscription_ready_to_renew: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        old_period_end = active_subscription_ready_to_renew.current_period_end
        assert old_period_end is not None
        service = ChargeRenewalService()
        payment = service.create_payment(
            active_subscription_ready_to_renew, paid_tariff, action=WebhookAction.RECURRING
        )
        service.process_payment(
            payment,
            paid_tariff,
            active_subscription_ready_to_renew,
            succeeded=True,
            period_start=old_period_end,
            failed_status=SubscriptionStatus.PAST_DUE,
        )
        active_subscription_ready_to_renew.refresh_from_db()
        assert active_subscription_ready_to_renew.current_period_start == old_period_end

    def test_sets_current_period_end_via_get_next_period_end(
        self,
        active_subscription_ready_to_renew: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        old_period_end = active_subscription_ready_to_renew.current_period_end
        assert old_period_end is not None
        expected_end = paid_tariff.get_next_period_end(old_period_end)
        service = ChargeRenewalService()
        payment = service.create_payment(
            active_subscription_ready_to_renew, paid_tariff, action=WebhookAction.RECURRING
        )
        service.process_payment(
            payment,
            paid_tariff,
            active_subscription_ready_to_renew,
            succeeded=True,
            period_start=old_period_end,
            failed_status=SubscriptionStatus.PAST_DUE,
        )
        active_subscription_ready_to_renew.refresh_from_db()
        assert active_subscription_ready_to_renew.current_period_end == expected_end

    def test_sets_payment_canceled_with_reason(
        self,
        active_subscription_ready_to_renew: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        service = ChargeRenewalService()
        payment = service.create_payment(
            active_subscription_ready_to_renew, paid_tariff, action=WebhookAction.RECURRING
        )
        period_start = active_subscription_ready_to_renew.current_period_end
        assert period_start is not None
        service.process_payment(
            payment,
            paid_tariff,
            active_subscription_ready_to_renew,
            succeeded=False,
            cancellation_reason='card_expired',
            period_start=period_start,
            failed_status=SubscriptionStatus.PAST_DUE,
        )
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.CANCELED
        assert payment.cancellation_reason == 'card_expired'

    def test_sets_subscription_past_due_on_failure(
        self,
        active_subscription_ready_to_renew: Subscription,
        paid_tariff: Tariff,
    ) -> None:
        service = ChargeRenewalService()
        payment = service.create_payment(
            active_subscription_ready_to_renew, paid_tariff, action=WebhookAction.RECURRING
        )
        period_start = active_subscription_ready_to_renew.current_period_end
        assert period_start is not None
        service.process_payment(
            payment,
            paid_tariff,
            active_subscription_ready_to_renew,
            succeeded=False,
            cancellation_reason='insufficient_funds',
            period_start=period_start,
            failed_status=SubscriptionStatus.PAST_DUE,
        )
        active_subscription_ready_to_renew.refresh_from_db()
        assert active_subscription_ready_to_renew.status == SubscriptionStatus.PAST_DUE

    def test_atomic_rollback_if_subscription_save_fails(
        self,
        active_subscription_ready_to_renew: Subscription,
        paid_tariff: Tariff,
        mocker: MockFixture,
    ) -> None:
        service = ChargeRenewalService()
        payment = service.create_payment(
            active_subscription_ready_to_renew, paid_tariff, action=WebhookAction.RECURRING
        )
        period_start = active_subscription_ready_to_renew.current_period_end
        assert period_start is not None
        mocker.patch.object(active_subscription_ready_to_renew, 'save', side_effect=Exception('db error'))
        with pytest.raises(Exception, match='db error'):
            service.process_payment(
                payment,
                paid_tariff,
                active_subscription_ready_to_renew,
                succeeded=True,
                period_start=period_start,
                failed_status=SubscriptionStatus.PAST_DUE,
            )
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.PENDING


class TestProcessSubscription:
    def test_happy_path_yookassa_succeeded(
        self,
        active_subscription_ready_to_renew: Subscription,
        paid_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
        yookassa_succeeded_response: MockType,
    ) -> None:
        mock_yookassa_payment_create.return_value = yookassa_succeeded_response
        service = ChargeRenewalService()
        service.process_subscription(active_subscription_ready_to_renew, paid_tariff)
        active_subscription_ready_to_renew.refresh_from_db()
        assert active_subscription_ready_to_renew.status == SubscriptionStatus.ACTIVE
        assert active_subscription_ready_to_renew.tariff == paid_tariff

    def test_skips_if_pending_recurring_payment_exists(
        self,
        active_subscription_ready_to_renew: Subscription,
        paid_tariff: Tariff,
        pending_recurring_payment_for_renewal: Payment,
    ) -> None:
        """check_pending_recurring_payment raises PaymentPendingRecurringError — no new payment created."""
        service = ChargeRenewalService()
        initial_count = Payment.objects.filter(subscription=active_subscription_ready_to_renew).count()
        with pytest.raises(PaymentPendingRecurringError):
            service.process_subscription(active_subscription_ready_to_renew, paid_tariff)
        assert Payment.objects.filter(subscription=active_subscription_ready_to_renew).count() == initial_count

    def test_cancels_payment_on_yookassa_failure_exception(
        self,
        active_subscription_ready_to_renew: Subscription,
        paid_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        mock_yookassa_payment_create.side_effect = Exception('gateway timeout')
        service = ChargeRenewalService()
        service.process_subscription(active_subscription_ready_to_renew, paid_tariff)
        payment = Payment.objects.filter(
            subscription=active_subscription_ready_to_renew,
            payment_type=PaymentType.RECURRING,
        ).latest('created_at')
        assert payment.status == PaymentStatus.CANCELED
        active_subscription_ready_to_renew.refresh_from_db()
        assert active_subscription_ready_to_renew.status == SubscriptionStatus.PAST_DUE

    def test_cancels_payment_on_yookassa_non_succeeded_status(
        self,
        active_subscription_ready_to_renew: Subscription,
        paid_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
        yookassa_canceled_response: MockType,
    ) -> None:
        mock_yookassa_payment_create.return_value = yookassa_canceled_response
        service = ChargeRenewalService()
        service.process_subscription(active_subscription_ready_to_renew, paid_tariff)
        payment = Payment.objects.filter(
            subscription=active_subscription_ready_to_renew,
            payment_type=PaymentType.RECURRING,
        ).latest('created_at')
        assert payment.status == PaymentStatus.CANCELED
        active_subscription_ready_to_renew.refresh_from_db()
        assert active_subscription_ready_to_renew.status == SubscriptionStatus.PAST_DUE

    def test_uses_pending_tariff_when_present(
        self,
        active_subscription_ready_to_renew: Subscription,
        paid_tariff: Tariff,
        upgrade_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
        yookassa_succeeded_response: MockType,
    ) -> None:
        """When pending_tariff is set, act() uses it as the new tariff."""
        active_subscription_ready_to_renew.pending_tariff = upgrade_tariff
        active_subscription_ready_to_renew.save(update_fields=['pending_tariff'])
        mock_yookassa_payment_create.return_value = yookassa_succeeded_response
        service = ChargeRenewalService()
        service()
        active_subscription_ready_to_renew.refresh_from_db()
        assert active_subscription_ready_to_renew.tariff == upgrade_tariff


class TestAct:
    def test_returns_zero_if_no_subscriptions(self) -> None:
        service = ChargeRenewalService()
        assert service() == 0

    def test_returns_count_of_processed_subscriptions(
        self,
        active_subscription_ready_to_renew: Subscription,
        paid_tariff: Tariff,
        mock_yookassa_payment_create: MockType,
        yookassa_succeeded_response: MockType,
    ) -> None:
        mock_yookassa_payment_create.return_value = yookassa_succeeded_response
        service = ChargeRenewalService()
        count = service()
        assert count == 1

    def test_continues_on_generic_exception(
        self,
        active_subscription_ready_to_renew: Subscription,
        paid_tariff: Tariff,
        mocker: MockFixture,
    ) -> None:
        mocker.patch.object(
            ChargeRenewalService,
            'process_subscription',
            side_effect=Exception('unexpected'),
        )
        service = ChargeRenewalService()
        count = service()
        assert count == 0

    def test_subscription_not_in_window_not_processed(
        self,
        active_subscription_ready_to_renew: Subscription,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        """Subscription with current_period_end far in the future is not in queryset."""
        active_subscription_ready_to_renew.current_period_end = timezone.now() + timedelta(hours=1)
        active_subscription_ready_to_renew.save(update_fields=['current_period_end'])
        service = ChargeRenewalService()
        count = service()
        assert count == 0
        mock_yookassa_payment_create.assert_not_called()

    def test_subscription_without_auto_renew_not_processed(
        self,
        active_subscription_ready_to_renew: Subscription,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        active_subscription_ready_to_renew.auto_renew = False
        active_subscription_ready_to_renew.save(update_fields=['auto_renew'])
        service = ChargeRenewalService()
        count = service()
        assert count == 0
        mock_yookassa_payment_create.assert_not_called()


class TestProcessSubscriptionRenewalsTask:
    def test_task_returns_formatted_string(
        self,
        active_subscription_ready_to_renew: Subscription,
        mock_yookassa_payment_create: MockType,
        yookassa_succeeded_response: MockType,
    ) -> None:
        mock_yookassa_payment_create.return_value = yookassa_succeeded_response
        result = process_subscription_renewals()
        assert 'Charged 1 renewals.' in result

    def test_task_calls_service(self, mocker: MockFixture) -> None:
        mock_call = mocker.patch.object(ChargeRenewalService, '__call__', return_value=0)
        result = process_subscription_renewals()
        mock_call.assert_called_once()
        assert 'Charged 0 renewals.' in result
