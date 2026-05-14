from pytest_mock import MockFixture, MockType

from decimal import Decimal

from django.conf import settings
from django.test import override_settings

import requests

from apps.subscriptions.models import Subscription
from apps.subscriptions.models.model_enums import PaymentStatus, PaymentType
from apps.subscriptions.models.payments import Payment
from apps.subscriptions.services.tax_check import TaxCheckSender
from apps.users.models import User

ENABLED = {'SEND_CHECKS_TO_TAX3R': True, 'TAX3R_URL': 'https://tax3r.example.com', 'TAX3R_API_KEY': 'test-key'}
DISABLED = {'SEND_CHECKS_TO_TAX3R': False}


def make_payment(subscription: Subscription, user: User, amount: str = '99.00') -> Payment:
    return Payment.objects.create(
        subscription=subscription,
        user=user,
        amount=Decimal(amount),
        payment_type=PaymentType.FIRST_PAYMENT,
        status=PaymentStatus.PENDING,
        idempotence_key='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        yookassa_payment_id='yoo-tax-test-001',
        metadata={},
    )


class TestTaxCheckSender:
    @override_settings(**DISABLED)
    def test_skips_if_flag_disabled(
        self,
        mock_tax3r_post: MockType,
        telegram_user: User,
        active_subscription: Subscription,
    ) -> None:
        """SEND_CHECKS_TO_TAX3R=False → requests.post is never called."""
        payment = make_payment(active_subscription, telegram_user)
        TaxCheckSender(payment=payment, service_name='Test')()
        mock_tax3r_post.assert_not_called()

    @override_settings(**ENABLED)
    def test_skips_if_amount_zero(
        self,
        mock_tax3r_post: MockType,
        telegram_user: User,
        active_subscription: Subscription,
    ) -> None:
        """amount=0 with flag enabled → requests.post is never called."""
        payment = make_payment(active_subscription, telegram_user, amount='0.00')
        TaxCheckSender(payment=payment, service_name='Test')()
        mock_tax3r_post.assert_not_called()

    @override_settings(**ENABLED)
    def test_sends_correct_request(
        self,
        mock_tax3r_post: MockType,
        telegram_user: User,
        active_subscription: Subscription,
    ) -> None:
        """Correct URL, header and body are passed to requests.post."""
        payment = make_payment(active_subscription, telegram_user, amount='99.00')
        TaxCheckSender(payment=payment, service_name='Подписка Edelya')()
        mock_tax3r_post.assert_called_once()
        args, kwargs = mock_tax3r_post.call_args
        url = args[0] if args else kwargs.get('url')
        assert url == 'https://tax3r.example.com/send_check'
        assert kwargs['headers'] == {'x-api-key': 'test-key'}
        assert kwargs['json'] == {
            'service_name': 'Подписка Edelya',
            'price': '99.00',
            'payment_id': str(payment.id),
            'service': settings.SERVICE_NAME,
        }
        assert kwargs['timeout'] == 10

    @override_settings(**ENABLED)
    def test_logs_info_on_success(
        self,
        mock_tax3r_post: MockType,
        mocker: MockFixture,
        telegram_user: User,
        active_subscription: Subscription,
    ) -> None:
        """Successful HTTP response → loki_logger.info is called."""
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_tax3r_post.return_value = mock_response
        mock_loki = mocker.patch('apps.subscriptions.services.tax_check.loki_logger')
        payment = make_payment(active_subscription, telegram_user)
        TaxCheckSender(payment=payment, service_name='Test')()
        mock_loki.info.assert_called_once()

    @override_settings(**ENABLED)
    def test_logs_error_on_http_error(
        self,
        mock_tax3r_post: MockType,
        mocker: MockFixture,
        telegram_user: User,
        active_subscription: Subscription,
    ) -> None:
        """HTTPError from raise_for_status → tg_logger.error called, exception not propagated."""
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError('500 Server Error')
        mock_tax3r_post.return_value = mock_response
        mock_tg = mocker.patch('apps.subscriptions.services.tax_check.tg_logger')
        payment = make_payment(active_subscription, telegram_user)
        TaxCheckSender(payment=payment, service_name='Test')()  # must not raise
        mock_tg.error.assert_called_once()

    @override_settings(**ENABLED)
    def test_logs_error_on_connection_error(
        self,
        mock_tax3r_post: MockType,
        mocker: MockFixture,
        telegram_user: User,
        active_subscription: Subscription,
    ) -> None:
        """ConnectionError → tg_logger.error called, exception not propagated."""
        mock_tax3r_post.side_effect = requests.ConnectionError('timeout')
        mock_tg = mocker.patch('apps.subscriptions.services.tax_check.tg_logger')
        payment = make_payment(active_subscription, telegram_user)
        TaxCheckSender(payment=payment, service_name='Test')()  # must not raise
        mock_tg.error.assert_called_once()
