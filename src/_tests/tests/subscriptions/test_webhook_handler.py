from pytest_mock import MockType

from datetime import timedelta
from unittest.mock import MagicMock

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.marketing.models import Notification
from apps.marketing.models.model_enums import MessageTemplateName
from apps.subscriptions.models import PaymentMethod, Subscription, Tariff
from apps.subscriptions.models.model_enums import PaymentStatus, PaymentType, SubscriptionStatus
from apps.subscriptions.models.payments import Payment
from apps.users.models import User

WEBHOOK_URL = reverse('api_v1:subscriptions:yookassa-webhook')


def make_payment_method_object(yookassa_id: str = 'yoo-pm-id-001') -> MagicMock:
    obj = MagicMock()
    obj.id = yookassa_id
    obj.type = 'bank_card'
    obj.title = 'Bank card *4242'
    obj.card.last4 = '4242'
    obj.card.card_type = 'Visa'
    return obj


def make_payment_object(yookassa_id: str, status_value: str = 'succeeded') -> MagicMock:
    obj = MagicMock()
    obj.id = yookassa_id
    obj.status = status_value
    obj.payment_method = make_payment_method_object(yookassa_id='yoo-pm-id-saved-001')
    obj.payment_method.saved = True
    return obj


def make_canceled_payment_object(yookassa_id: str, reason: str = 'card_expired') -> MagicMock:
    obj = MagicMock()
    obj.id = yookassa_id
    obj.status = 'canceled'
    obj.cancellation_details.reason = reason
    return obj


class TestWebhookEndpoint:
    def test_unknown_event_returns_200(self, api_client: APIClient) -> None:
        """Неизвестное событие не роняет ендпоинт — YooKassa всегда получает 200 OK."""
        response = api_client.post(
            WEBHOOK_URL,
            data={'event': 'some.unknown.event', 'object': {}},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK

    def test_missing_payment_returns_200(self, api_client: APIClient) -> None:
        """Payment не найден в БД — исключение поглощается, ендпоинт возвращает 200 OK."""
        response = api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment.succeeded',
                'object': {'id': 'nonexistent-yoo-id'},
            },
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK

    def test_empty_body_returns_200(self, api_client: APIClient) -> None:
        """Пустое тело не роняет ендпоинт."""
        response = api_client.post(WEBHOOK_URL, data={}, format='json')
        assert response.status_code == status.HTTP_200_OK


class TestPaymentMethodActiveHandler:
    def test_upserts_payment_method(
        self,
        api_client: APIClient,
        telegram_user: User,
        pending_payment_zero_amount: Payment,
    ) -> None:
        """payment_method.active создаёт PaymentMethod в БД с данными карты из YooKassa."""
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment_method.active',
                'object': {
                    'id': 'yoo-pm-id-001',
                    'type': 'bank_card',
                    'title': 'Bank card *4242',
                    'saved': True,
                    'card': {'last4': '4242', 'card_type': 'Visa'},
                },
            },
            format='json',
        )
        pm = PaymentMethod.objects.get(user=telegram_user)
        assert pm.yookassa_payment_method_id == 'yoo-pm-id-001'
        assert pm.card_last4 == '4242'
        assert pm.card_type == 'Visa'
        assert pm.is_active is True

    def test_links_payment_method_to_subscription(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
        pending_payment_zero_amount: Payment,
    ) -> None:
        """payment_method.active привязывает PaymentMethod к подписке."""
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment_method.active',
                'object': {
                    'id': 'yoo-pm-id-001',
                    'type': 'bank_card',
                    'title': 'Bank card *4242',
                    'saved': True,
                    'card': {'last4': '4242', 'card_type': 'Visa'},
                },
            },
            format='json',
        )
        trial_subscription.refresh_from_db()
        assert trial_subscription.payment_method is not None
        assert trial_subscription.payment_method.yookassa_payment_method_id == 'yoo-pm-id-001'

    def test_sets_pending_tariff_when_tariff_id_in_metadata(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
        paid_tariff: Tariff,
        pending_payment_zero_amount_with_tariff: Payment,
    ) -> None:
        """payment_method.active с tariff_id в metadata устанавливает pending_tariff на подписке."""
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment_method.active',
                'object': {
                    'id': 'yoo-pm-id-001',
                    'type': 'bank_card',
                    'title': 'Bank card *4242',
                    'saved': True,
                    'card': {'last4': '4242', 'card_type': 'Visa'},
                },
            },
            format='json',
        )
        trial_subscription.refresh_from_db()
        assert trial_subscription.pending_tariff == paid_tariff

    def test_does_not_set_pending_tariff_without_tariff_id_in_metadata(
        self,
        api_client: APIClient,
        telegram_user: User,
        trial_subscription: Subscription,
        pending_payment_zero_amount: Payment,
    ) -> None:
        """payment_method.active без tariff_id в metadata не трогает pending_tariff."""
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment_method.active',
                'object': {
                    'id': 'yoo-pm-id-001',
                    'type': 'bank_card',
                    'title': 'Bank card *4242',
                    'saved': True,
                    'card': {'last4': '4242', 'card_type': 'Visa'},
                },
            },
            format='json',
        )
        trial_subscription.refresh_from_db()
        assert trial_subscription.pending_tariff is None

    def test_marks_payment_as_succeeded(
        self,
        api_client: APIClient,
        telegram_user: User,
        pending_payment_zero_amount: Payment,
    ) -> None:
        """payment_method.active переводит связанный Payment в статус SUCCEEDED."""
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment_method.active',
                'object': {
                    'id': 'yoo-pm-id-001',
                    'type': 'bank_card',
                    'title': 'Bank card *4242',
                    'saved': True,
                    'card': {'last4': '4242', 'card_type': 'Visa'},
                },
            },
            format='json',
        )
        pending_payment_zero_amount.refresh_from_db()
        assert pending_payment_zero_amount.status == PaymentStatus.SUCCEEDED

    def test_idempotent_on_repeat_call(
        self,
        api_client: APIClient,
        telegram_user: User,
        pending_payment_zero_amount: Payment,
    ) -> None:
        """Повторный вебхук payment_method.active не создаёт дублей и не падает."""
        payload = {
            'event': 'payment_method.active',
            'object': {
                'id': 'yoo-pm-id-001',
                'type': 'bank_card',
                'title': 'Bank card *4242',
                'saved': True,
                'card': {'last4': '4242', 'card_type': 'Visa'},
            },
        }
        api_client.post(WEBHOOK_URL, data=payload, format='json')
        api_client.post(WEBHOOK_URL, data=payload, format='json')
        assert PaymentMethod.objects.filter(user=telegram_user).count() == 1

    def test_sends_card_bound_notification(
        self,
        api_client: APIClient,
        telegram_user: User,
        pending_payment_zero_amount: Payment,
    ) -> None:
        """payment_method.active отправляет уведомление о привязке карты."""
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment_method.active',
                'object': {
                    'id': 'yoo-pm-id-001',
                    'type': 'bank_card',
                    'title': 'Bank card *4242',
                    'saved': True,
                    'card': {'last4': '4242', 'card_type': 'Visa'},
                },
            },
            format='json',
        )
        assert Notification.objects.filter(
            user=telegram_user,
            template__name=MessageTemplateName.SUBSCRIPTION_CARD_BOUND,
            delivered=True,
        ).exists()


class TestPaymentSucceededHandlerFirstPayment:
    def test_activates_subscription(
        self,
        api_client: APIClient,
        telegram_user: User,
        expired_subscription: Subscription,
        paid_tariff: Tariff,
        pending_payment_first: Payment,
    ) -> None:
        """payment.succeeded (FIRST_PAYMENT) переводит подписку в статус ACTIVE."""
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment.succeeded',
                'object': {
                    'id': 'yoo-pay-id-001',
                    'status': 'succeeded',
                    'amount': {'value': str(paid_tariff.price), 'currency': 'RUB'},
                    'payment_method': {
                        'id': 'yoo-pm-id-saved-001',
                        'type': 'bank_card',
                        'saved': True,
                        'title': 'Bank card *4242',
                        'card': {'last4': '4242', 'card_type': 'Visa'},
                    },
                    'metadata': {'action': 'first_payment', 'tariff_id': str(paid_tariff.id)},
                },
            },
            format='json',
        )
        expired_subscription.refresh_from_db()
        assert expired_subscription.status == SubscriptionStatus.ACTIVE

    def test_sets_correct_tariff_on_subscription(
        self,
        api_client: APIClient,
        telegram_user: User,
        expired_subscription: Subscription,
        paid_tariff: Tariff,
        pending_payment_first: Payment,
    ) -> None:
        """payment.succeeded (FIRST_PAYMENT) устанавливает выбранный тариф на подписке."""
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment.succeeded',
                'object': {
                    'id': 'yoo-pay-id-001',
                    'status': 'succeeded',
                    'amount': {'value': str(paid_tariff.price), 'currency': 'RUB'},
                    'payment_method': {
                        'id': 'yoo-pm-id-saved-001',
                        'type': 'bank_card',
                        'saved': True,
                        'title': 'Bank card *4242',
                        'card': {'last4': '4242', 'card_type': 'Visa'},
                    },
                    'metadata': {'action': 'first_payment', 'tariff_id': str(paid_tariff.id)},
                },
            },
            format='json',
        )
        expired_subscription.refresh_from_db()
        assert expired_subscription.tariff == paid_tariff

    def test_sets_billing_period_on_subscription(
        self,
        api_client: APIClient,
        telegram_user: User,
        expired_subscription: Subscription,
        paid_tariff: Tariff,
        pending_payment_first: Payment,
    ) -> None:
        """payment.succeeded (FIRST_PAYMENT) выставляет current_period_start и current_period_end."""
        before = timezone.now()
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment.succeeded',
                'object': {
                    'id': 'yoo-pay-id-001',
                    'status': 'succeeded',
                    'amount': {'value': str(paid_tariff.price), 'currency': 'RUB'},
                    'payment_method': {
                        'id': 'yoo-pm-id-saved-001',
                        'type': 'bank_card',
                        'saved': True,
                        'title': 'Bank card *4242',
                        'card': {'last4': '4242', 'card_type': 'Visa'},
                    },
                    'metadata': {'action': 'first_payment', 'tariff_id': str(paid_tariff.id)},
                },
            },
            format='json',
        )
        expired_subscription.refresh_from_db()
        assert expired_subscription.current_period_start and expired_subscription.current_period_end
        assert expired_subscription.current_period_start >= before
        assert expired_subscription.current_period_end > expired_subscription.current_period_start

    def test_clears_cancelled_at(
        self,
        api_client: APIClient,
        telegram_user: User,
        expired_subscription: Subscription,
        paid_tariff: Tariff,
        pending_payment_first: Payment,
    ) -> None:
        """payment.succeeded (FIRST_PAYMENT) сбрасывает cancelled_at при реактивации."""
        expired_subscription.cancelled_at = timezone.now() - timedelta(days=5)
        expired_subscription.save(update_fields=['cancelled_at'])
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment.succeeded',
                'object': {
                    'id': 'yoo-pay-id-001',
                    'status': 'succeeded',
                    'amount': {'value': str(paid_tariff.price), 'currency': 'RUB'},
                    'payment_method': {
                        'id': 'yoo-pm-id-saved-001',
                        'type': 'bank_card',
                        'saved': True,
                        'title': 'Bank card *4242',
                        'card': {'last4': '4242', 'card_type': 'Visa'},
                    },
                    'metadata': {'action': 'first_payment', 'tariff_id': str(paid_tariff.id)},
                },
            },
            format='json',
        )
        expired_subscription.refresh_from_db()
        assert expired_subscription.cancelled_at is None

    def test_upserts_payment_method_and_links_to_subscription(
        self,
        api_client: APIClient,
        telegram_user: User,
        expired_subscription: Subscription,
        paid_tariff: Tariff,
        pending_payment_first: Payment,
    ) -> None:
        """payment.succeeded создаёт PaymentMethod и привязывает его к подписке."""
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment.succeeded',
                'object': {
                    'id': 'yoo-pay-id-001',
                    'status': 'succeeded',
                    'amount': {'value': str(paid_tariff.price), 'currency': 'RUB'},
                    'payment_method': {
                        'id': 'yoo-pm-id-saved-001',
                        'type': 'bank_card',
                        'saved': True,
                        'title': 'Bank card *4242',
                        'card': {'last4': '4242', 'card_type': 'Visa'},
                    },
                    'metadata': {'action': 'first_payment', 'tariff_id': str(paid_tariff.id)},
                },
            },
            format='json',
        )
        expired_subscription.refresh_from_db()
        assert expired_subscription.payment_method is not None
        assert expired_subscription.payment_method.yookassa_payment_method_id == 'yoo-pm-id-saved-001'

    def test_marks_payment_as_succeeded_with_paid_at(
        self,
        api_client: APIClient,
        telegram_user: User,
        expired_subscription: Subscription,
        paid_tariff: Tariff,
        pending_payment_first: Payment,
    ) -> None:
        """payment.succeeded переводит Payment в SUCCEEDED и заполняет paid_at."""
        before = timezone.now()
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment.succeeded',
                'object': {
                    'id': 'yoo-pay-id-001',
                    'status': 'succeeded',
                    'amount': {'value': str(paid_tariff.price), 'currency': 'RUB'},
                    'payment_method': {
                        'id': 'yoo-pm-id-saved-001',
                        'type': 'bank_card',
                        'saved': True,
                        'title': 'Bank card *4242',
                        'card': {'last4': '4242', 'card_type': 'Visa'},
                    },
                    'metadata': {'action': 'first_payment', 'tariff_id': str(paid_tariff.id)},
                },
            },
            format='json',
        )
        pending_payment_first.refresh_from_db()
        assert pending_payment_first.status == PaymentStatus.SUCCEEDED
        assert pending_payment_first.paid_at is not None
        assert pending_payment_first.paid_at >= before

    def test_idempotent_on_repeat_call(
        self,
        api_client: APIClient,
        telegram_user: User,
        expired_subscription: Subscription,
        paid_tariff: Tariff,
        pending_payment_first: Payment,
    ) -> None:
        """Повторный payment.succeeded не изменяет данные, уже обработанные первым вызовом."""
        payload = {
            'event': 'payment.succeeded',
            'object': {
                'id': 'yoo-pay-id-001',
                'status': 'succeeded',
                'amount': {'value': str(paid_tariff.price), 'currency': 'RUB'},
                'payment_method': {
                    'id': 'yoo-pm-id-saved-001',
                    'type': 'bank_card',
                    'saved': True,
                    'title': 'Bank card *4242',
                    'card': {'last4': '4242', 'card_type': 'Visa'},
                },
                'metadata': {'action': 'first_payment', 'tariff_id': str(paid_tariff.id)},
            },
        }
        api_client.post(WEBHOOK_URL, data=payload, format='json')
        first_paid_at = Payment.objects.get(id=pending_payment_first.id).paid_at
        api_client.post(WEBHOOK_URL, data=payload, format='json')
        second_paid_at = Payment.objects.get(id=pending_payment_first.id).paid_at
        assert first_paid_at == second_paid_at

    def test_sends_first_payment_notification(
        self,
        api_client: APIClient,
        telegram_user: User,
        expired_subscription: Subscription,
        paid_tariff: Tariff,
        pending_payment_first: Payment,
    ) -> None:
        """payment.succeeded (FIRST_PAYMENT) отправляет уведомление об активации подписки."""
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment.succeeded',
                'object': {
                    'id': 'yoo-pay-id-001',
                    'status': 'succeeded',
                    'amount': {'value': str(paid_tariff.price), 'currency': 'RUB'},
                    'payment_method': {
                        'id': 'yoo-pm-id-saved-001',
                        'type': 'bank_card',
                        'saved': True,
                        'title': 'Bank card *4242',
                        'card': {'last4': '4242', 'card_type': 'Visa'},
                    },
                    'metadata': {'action': 'first_payment', 'tariff_id': str(paid_tariff.id)},
                },
            },
            format='json',
        )
        assert Notification.objects.filter(
            user=telegram_user,
            template__name=MessageTemplateName.SUBSCRIPTION_FIRST_PAYMENT_SUCCEEDED,
            delivered=True,
        ).exists()


class TestPaymentSucceededHandlerRecurring:
    def test_renews_subscription_period(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        paid_tariff: Tariff,
        pending_payment_recurring: Payment,
    ) -> None:
        """payment.succeeded (RECURRING) продлевает period_start и period_end подписки."""
        old_period_end = active_subscription_with_period.current_period_end
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment.succeeded',
                'object': {
                    'id': 'yoo-pay-id-recurring-001',
                    'status': 'succeeded',
                    'amount': {'value': str(paid_tariff.price), 'currency': 'RUB'},
                    'payment_method': {
                        'id': 'yoo-pm-id-saved-001',
                        'type': 'bank_card',
                        'saved': True,
                        'title': 'Bank card *4242',
                        'card': {'last4': '4242', 'card_type': 'Visa'},
                    },
                    'metadata': {'action': 'recurring'},
                },
            },
            format='json',
        )
        active_subscription_with_period.refresh_from_db()
        assert (
            active_subscription_with_period.current_period_start and active_subscription_with_period.current_period_end
        )
        assert active_subscription_with_period.current_period_start == old_period_end
        assert active_subscription_with_period.current_period_end > old_period_end

    def test_sets_status_to_active_on_past_due(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        paid_tariff: Tariff,
        pending_payment_recurring: Payment,
    ) -> None:
        """payment.succeeded (RECURRING) поднимает статус PAST_DUE → ACTIVE."""
        active_subscription_with_period.status = SubscriptionStatus.PAST_DUE
        active_subscription_with_period.save(update_fields=['status'])
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment.succeeded',
                'object': {
                    'id': 'yoo-pay-id-recurring-001',
                    'status': 'succeeded',
                    'amount': {'value': str(paid_tariff.price), 'currency': 'RUB'},
                    'payment_method': {
                        'id': 'yoo-pm-id-saved-001',
                        'type': 'bank_card',
                        'saved': True,
                        'title': 'Bank card *4242',
                        'card': {'last4': '4242', 'card_type': 'Visa'},
                    },
                    'metadata': {'action': 'recurring'},
                },
            },
            format='json',
        )
        active_subscription_with_period.refresh_from_db()
        assert active_subscription_with_period.status == SubscriptionStatus.ACTIVE

    def test_sends_recurring_payment_notification(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        paid_tariff: Tariff,
        pending_payment_recurring: Payment,
    ) -> None:
        """payment.succeeded (RECURRING) отправляет уведомление о продлении подписки."""
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment.succeeded',
                'object': {
                    'id': 'yoo-pay-id-recurring-001',
                    'status': 'succeeded',
                    'amount': {'value': str(paid_tariff.price), 'currency': 'RUB'},
                    'payment_method': {
                        'id': 'yoo-pm-id-saved-001',
                        'type': 'bank_card',
                        'saved': True,
                        'title': 'Bank card *4242',
                        'card': {'last4': '4242', 'card_type': 'Visa'},
                    },
                    'metadata': {'action': 'recurring'},
                },
            },
            format='json',
        )
        assert Notification.objects.filter(
            user=telegram_user,
            template__name=MessageTemplateName.SUBSCRIPTION_RECURRING_PAYMENT_SUCCEEDED,
            delivered=True,
        ).exists()


class TestPaymentCanceledHandler:
    def test_marks_payment_as_canceled(
        self,
        api_client: APIClient,
        telegram_user: User,
        expired_subscription: Subscription,
        paid_tariff: Tariff,
        pending_payment_first: Payment,
    ) -> None:
        """payment.canceled переводит Payment в статус CANCELED."""
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment.canceled',
                'object': {
                    'id': 'yoo-pay-id-001',
                    'status': 'canceled',
                    'cancellation_details': {'party': 'yoo_money', 'reason': 'card_expired'},
                },
            },
            format='json',
        )
        pending_payment_first.refresh_from_db()
        assert pending_payment_first.status == PaymentStatus.CANCELED

    def test_saves_cancellation_reason(
        self,
        api_client: APIClient,
        telegram_user: User,
        expired_subscription: Subscription,
        paid_tariff: Tariff,
        pending_payment_first: Payment,
    ) -> None:
        """payment.canceled сохраняет причину отмены из cancellation_details.reason."""
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment.canceled',
                'object': {
                    'id': 'yoo-pay-id-001',
                    'status': 'canceled',
                    'cancellation_details': {'party': 'yoo_money', 'reason': 'card_expired'},
                },
            },
            format='json',
        )
        pending_payment_first.refresh_from_db()
        assert pending_payment_first.cancellation_reason == 'card_expired'

    def test_does_not_change_subscription_status_on_first_payment_cancel(
        self,
        api_client: APIClient,
        telegram_user: User,
        expired_subscription: Subscription,
        paid_tariff: Tariff,
        pending_payment_first: Payment,
    ) -> None:
        """payment.canceled для FIRST_PAYMENT не меняет статус подписки — она остаётся EXPIRED."""
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment.canceled',
                'object': {
                    'id': 'yoo-pay-id-001',
                    'status': 'canceled',
                    'cancellation_details': {'party': 'yoo_money', 'reason': 'card_expired'},
                },
            },
            format='json',
        )
        expired_subscription.refresh_from_db()
        assert expired_subscription.status == SubscriptionStatus.EXPIRED

    def test_idempotent_on_repeat_call(
        self,
        api_client: APIClient,
        telegram_user: User,
        expired_subscription: Subscription,
        paid_tariff: Tariff,
        pending_payment_first: Payment,
    ) -> None:
        """Повторный payment.canceled не изменяет уже записанные данные."""
        payload = {
            'event': 'payment.canceled',
            'object': {
                'id': 'yoo-pay-id-001',
                'status': 'canceled',
                'cancellation_details': {'party': 'yoo_money', 'reason': 'card_expired'},
            },
        }
        api_client.post(WEBHOOK_URL, data=payload, format='json')
        api_client.post(WEBHOOK_URL, data=payload, format='json')
        pending_payment_first.refresh_from_db()
        assert pending_payment_first.status == PaymentStatus.CANCELED

    def test_sends_payment_failed_notification(
        self,
        api_client: APIClient,
        telegram_user: User,
        expired_subscription: Subscription,
        paid_tariff: Tariff,
        pending_payment_first: Payment,
    ) -> None:
        """payment.canceled отправляет уведомление о неудачном платеже."""
        api_client.post(
            WEBHOOK_URL,
            data={
                'event': 'payment.canceled',
                'object': {
                    'id': 'yoo-pay-id-001',
                    'status': 'canceled',
                    'cancellation_details': {'party': 'yoo_money', 'reason': 'card_expired'},
                },
            },
            format='json',
        )
        assert Notification.objects.filter(
            user=telegram_user,
            template__name=MessageTemplateName.SUBSCRIPTION_PAYMENT_FAILED,
            delivered=True,
        ).exists()


UPGRADE_SUCCEEDED_PAYLOAD = {
    'event': 'payment.succeeded',
    'object': {
        'id': 'yoo-pay-id-upgrade-001',
        'status': 'succeeded',
        'amount': {'value': '50.00', 'currency': 'RUB'},
        'payment_method': {
            'id': 'yoo-pm-id-saved-001',
            'type': 'bank_card',
            'saved': True,
            'title': 'Bank card *4242',
            'card': {'last4': '4242', 'card_type': 'Visa'},
        },
        'metadata': {'action': 'upgrade', 'tariff_id': 'some-uuid'},
    },
}


class TestPaymentSucceededHandlerUpgrade:
    def test_marks_payment_as_succeeded_with_paid_at(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        upgrade_tariff: Tariff,
        pending_payment_upgrade: Payment,
    ) -> None:
        """payment.succeeded (UPGRADE) переводит Payment в SUCCEEDED и заполняет paid_at."""
        before = timezone.now()
        api_client.post(WEBHOOK_URL, data=UPGRADE_SUCCEEDED_PAYLOAD, format='json')
        pending_payment_upgrade.refresh_from_db()
        assert pending_payment_upgrade.status == PaymentStatus.SUCCEEDED
        assert pending_payment_upgrade.paid_at is not None
        assert pending_payment_upgrade.paid_at >= before

    def test_saves_payment_method_on_payment(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        upgrade_tariff: Tariff,
        pending_payment_upgrade: Payment,
    ) -> None:
        """payment.succeeded (UPGRADE) сохраняет payment_method на Payment."""
        api_client.post(WEBHOOK_URL, data=UPGRADE_SUCCEEDED_PAYLOAD, format='json')
        pending_payment_upgrade.refresh_from_db()
        assert pending_payment_upgrade.payment_method is not None
        assert pending_payment_upgrade.payment_method.yookassa_payment_method_id == 'yoo-pm-id-saved-001'

    def test_does_not_change_subscription_period(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        upgrade_tariff: Tariff,
        pending_payment_upgrade: Payment,
    ) -> None:
        """payment.succeeded (UPGRADE) не трогает период подписки — он уже был сброшен при апгрейде."""
        original_period_start = active_subscription_with_period.current_period_start
        original_period_end = active_subscription_with_period.current_period_end
        api_client.post(WEBHOOK_URL, data=UPGRADE_SUCCEEDED_PAYLOAD, format='json')
        active_subscription_with_period.refresh_from_db()
        assert active_subscription_with_period.current_period_start == original_period_start
        assert active_subscription_with_period.current_period_end == original_period_end

    def test_does_not_change_subscription_status(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        upgrade_tariff: Tariff,
        pending_payment_upgrade: Payment,
    ) -> None:
        """payment.succeeded (UPGRADE) не меняет статус подписки — она остаётся ACTIVE."""
        api_client.post(WEBHOOK_URL, data=UPGRADE_SUCCEEDED_PAYLOAD, format='json')
        active_subscription_with_period.refresh_from_db()
        assert active_subscription_with_period.status == SubscriptionStatus.ACTIVE

    def test_idempotent_on_repeat_call(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        upgrade_tariff: Tariff,
        pending_payment_upgrade: Payment,
    ) -> None:
        """Повторный payment.succeeded (UPGRADE) не изменяет уже записанные данные."""
        api_client.post(WEBHOOK_URL, data=UPGRADE_SUCCEEDED_PAYLOAD, format='json')
        first_paid_at = Payment.objects.get(id=pending_payment_upgrade.id).paid_at
        api_client.post(WEBHOOK_URL, data=UPGRADE_SUCCEEDED_PAYLOAD, format='json')
        second_paid_at = Payment.objects.get(id=pending_payment_upgrade.id).paid_at
        assert first_paid_at == second_paid_at

    def test_payment_type_is_single_payment(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        upgrade_tariff: Tariff,
        pending_payment_upgrade: Payment,
    ) -> None:
        """Апгрейд-платёж имеет тип SINGLE_PAYMENT, а не RECURRING."""
        assert pending_payment_upgrade.payment_type == PaymentType.SINGLE_PAYMENT


class TestPaymentSucceededTaxCheck:
    """Verify that TaxCheckSender is triggered on paid webhooks and skipped on zero-amount ones."""

    def _first_payment_payload(self, tariff: Tariff) -> dict:
        return {
            'event': 'payment.succeeded',
            'object': {
                'id': 'yoo-pay-id-001',
                'status': 'succeeded',
                'amount': {'value': str(tariff.price), 'currency': 'RUB'},
                'payment_method': {
                    'id': 'yoo-pm-id-saved-001',
                    'type': 'bank_card',
                    'saved': True,
                    'title': 'Bank card *4242',
                    'card': {'last4': '4242', 'card_type': 'Visa'},
                },
                'metadata': {'action': 'first_payment', 'tariff_id': str(tariff.id)},
            },
        }

    def _recurring_payload(self) -> dict:
        return {
            'event': 'payment.succeeded',
            'object': {
                'id': 'yoo-pay-id-recurring-001',
                'status': 'succeeded',
                'amount': {'value': '99.00', 'currency': 'RUB'},
                'payment_method': {
                    'id': 'yoo-pm-id-saved-001',
                    'type': 'bank_card',
                    'saved': True,
                    'title': 'Bank card *4242',
                    'card': {'last4': '4242', 'card_type': 'Visa'},
                },
                'metadata': {'action': 'recurring'},
            },
        }

    def test_sends_tax_check_on_first_payment(
        self,
        api_client: APIClient,
        mock_tax3r_post: MockType,
        telegram_user: User,
        expired_subscription: Subscription,
        paid_tariff: Tariff,
        pending_payment_first: Payment,
    ) -> None:
        """FIRST_PAYMENT triggers one tax check call with service_name containing tariff name."""
        with override_settings(SEND_CHECKS_TO_TAX3R=True, TAX3R_URL='https://tax3r.example.com', TAX3R_API_KEY='k'):
            api_client.post(WEBHOOK_URL, data=self._first_payment_payload(paid_tariff), format='json')
        mock_tax3r_post.assert_called_once()
        body = mock_tax3r_post.call_args[1]['json']
        assert paid_tariff.name in body['service_name']

    def test_sends_tax_check_on_recurring(
        self,
        api_client: APIClient,
        mock_tax3r_post: MockType,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        paid_tariff: Tariff,
        pending_payment_recurring: Payment,
    ) -> None:
        """RECURRING triggers one tax check call with service_name containing tariff name."""
        with override_settings(SEND_CHECKS_TO_TAX3R=True, TAX3R_URL='https://tax3r.example.com', TAX3R_API_KEY='k'):
            api_client.post(WEBHOOK_URL, data=self._recurring_payload(), format='json')
        mock_tax3r_post.assert_called_once()
        body = mock_tax3r_post.call_args[1]['json']
        assert paid_tariff.name in body['service_name']

    def test_no_tax_check_on_upgrade_action(
        self,
        api_client: APIClient,
        mock_tax3r_post: MockType,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        upgrade_tariff: Tariff,
        pending_payment_upgrade: Payment,
    ) -> None:
        """UPGRADE webhook handler does not call tax check (already handled synchronously)."""
        with override_settings(SEND_CHECKS_TO_TAX3R=True, TAX3R_URL='https://tax3r.example.com', TAX3R_API_KEY='k'):
            api_client.post(WEBHOOK_URL, data=UPGRADE_SUCCEEDED_PAYLOAD, format='json')
        mock_tax3r_post.assert_not_called()

    def test_no_tax_check_on_zero_amount(
        self,
        api_client: APIClient,
        mock_tax3r_post: MockType,
        telegram_user: User,
        trial_subscription: Subscription,
        pending_payment_zero_amount: Payment,
    ) -> None:
        """Zero-amount card binding payment → TaxCheckSender skips the call."""
        with override_settings(SEND_CHECKS_TO_TAX3R=True, TAX3R_URL='https://tax3r.example.com', TAX3R_API_KEY='k'):
            api_client.post(
                WEBHOOK_URL,
                data={
                    'event': 'payment_method.active',
                    'object': {
                        'id': 'yoo-pm-id-001',
                        'type': 'bank_card',
                        'title': 'Bank card *4242',
                        'saved': True,
                        'card': {'last4': '4242', 'card_type': 'Visa'},
                    },
                },
                format='json',
            )
        mock_tax3r_post.assert_not_called()
