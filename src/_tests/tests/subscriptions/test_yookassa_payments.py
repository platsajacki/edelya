import pytest
from pytest_mock import MockerFixture, MockType

from decimal import Decimal

from pytest_django.fixtures import SettingsWrapper

from apps.subscriptions.services.yookassa_payments import YookassaPaymentsService


@pytest.fixture
def service(mocker: MockerFixture) -> YookassaPaymentsService:
    mocker.patch('apps.subscriptions.services.yookassa_payments.Configuration.configure')
    # Reset singleton so Configuration.configure is called through the mock
    if hasattr(YookassaPaymentsService, '_instance'):
        del YookassaPaymentsService._instance
    svc = YookassaPaymentsService()
    return svc


class TestYookassaPaymentsServiceCreatePayment:
    def test_create_payment_calls_yookassa_with_correct_params(
        self,
        service: YookassaPaymentsService,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        service.create_payment(amount=Decimal('100.00'), currency='RUB')
        mock_yookassa_payment_create.assert_called_once()
        call_params = mock_yookassa_payment_create.call_args[0][0]
        assert call_params['amount']['value'] == '100.00'
        assert call_params['amount']['currency'] == 'RUB'
        assert call_params['capture'] is True

    def test_create_payment_description_truncated_at_128_chars(
        self,
        service: YookassaPaymentsService,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        long_description = 'x' * 200
        service.create_payment(amount=Decimal('10.00'), description=long_description)
        call_params = mock_yookassa_payment_create.call_args[0][0]
        assert call_params['description'] == 'x' * 128

    def test_create_payment_with_payment_method_id_omits_confirmation(
        self,
        service: YookassaPaymentsService,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        service.create_payment(
            amount=Decimal('50.00'),
            payment_method_id='pm-existing-id',
            return_url='https://example.com/return',
        )
        call_params = mock_yookassa_payment_create.call_args[0][0]
        assert call_params['payment_method_id'] == 'pm-existing-id'
        assert 'confirmation' not in call_params

    def test_create_payment_without_payment_method_id_includes_confirmation(
        self,
        service: YookassaPaymentsService,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        service.create_payment(
            amount=Decimal('50.00'),
            return_url='https://example.com/return',
        )
        call_params = mock_yookassa_payment_create.call_args[0][0]
        assert 'confirmation' in call_params
        assert call_params['confirmation']['type'] == 'redirect'
        assert call_params['confirmation']['return_url'] == 'https://example.com/return'

    def test_create_payment_falls_back_to_settings_return_url(
        self,
        service: YookassaPaymentsService,
        mock_yookassa_payment_create: MockType,
        settings: SettingsWrapper,
    ) -> None:
        settings.YOOKASSA_RETURN_URL = 'https://settings.example.com/return'
        service.create_payment(amount=Decimal('50.00'))
        call_params = mock_yookassa_payment_create.call_args[0][0]
        assert call_params['confirmation']['return_url'] == 'https://settings.example.com/return'

    def test_create_payment_with_save_payment_method_true(
        self,
        service: YookassaPaymentsService,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        service.create_payment(amount=Decimal('100.00'), save_payment_method=True)
        call_params = mock_yookassa_payment_create.call_args[0][0]
        assert call_params['save_payment_method'] is True

    def test_create_payment_with_metadata(
        self,
        service: YookassaPaymentsService,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        metadata = {'user_id': 'abc-123', 'type': 'first_payment'}
        service.create_payment(amount=Decimal('100.00'), metadata=metadata)
        call_params = mock_yookassa_payment_create.call_args[0][0]
        assert call_params['metadata'] == metadata

    def test_create_payment_auto_generates_idempotence_key(
        self,
        service: YookassaPaymentsService,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        service.create_payment(amount=Decimal('100.00'))
        _, kwargs = mock_yookassa_payment_create.call_args
        assert 'idempotency_key' in kwargs
        assert kwargs['idempotency_key'] is not None

    def test_create_payment_uses_provided_idempotence_key(
        self,
        service: YookassaPaymentsService,
        mock_yookassa_payment_create: MockType,
    ) -> None:
        key = 'my-custom-key-123'
        service.create_payment(amount=Decimal('100.00'), idempotence_key=key)
        _, kwargs = mock_yookassa_payment_create.call_args
        assert kwargs['idempotency_key'] == key


class TestYookassaPaymentsServiceGetPayment:
    def test_get_payment_calls_find_one(
        self,
        service: YookassaPaymentsService,
        mock_yookassa_payment_find_one: MockType,
    ) -> None:
        service.get_payment('payment-id-123')
        mock_yookassa_payment_find_one.assert_called_once_with('payment-id-123')


class TestYookassaPaymentsServiceCapturePayment:
    def test_capture_payment_without_amount_passes_none_params(
        self,
        service: YookassaPaymentsService,
        mock_yookassa_payment_capture: MockType,
    ) -> None:
        service.capture_payment('payment-id-123')
        args = mock_yookassa_payment_capture.call_args[0]
        assert args[0] == 'payment-id-123'
        assert args[1] is None  # params

    def test_capture_payment_with_amount_passes_amount_params(
        self,
        service: YookassaPaymentsService,
        mock_yookassa_payment_capture: MockType,
    ) -> None:
        service.capture_payment('payment-id-123', amount=Decimal('75.00'), currency='RUB')
        args = mock_yookassa_payment_capture.call_args[0]
        assert args[1] == {'amount': {'value': '75.00', 'currency': 'RUB'}}


class TestYookassaPaymentsServiceCancelPayment:
    def test_cancel_payment_calls_yookassa_cancel(
        self,
        service: YookassaPaymentsService,
        mock_yookassa_payment_cancel: MockType,
    ) -> None:
        service.cancel_payment('payment-id-123')
        args = mock_yookassa_payment_cancel.call_args[0]
        assert args[0] == 'payment-id-123'

    def test_cancel_payment_auto_generates_idempotence_key(
        self,
        service: YookassaPaymentsService,
        mock_yookassa_payment_cancel: MockType,
    ) -> None:
        service.cancel_payment('payment-id-123')
        _, kwargs = mock_yookassa_payment_cancel.call_args
        assert 'idempotency_key' in kwargs
        assert kwargs['idempotency_key'] is not None


class TestYookassaPaymentsServicePaymentMethodBinding:
    def test_create_payment_method_binding_uses_provided_return_url(
        self,
        service: YookassaPaymentsService,
        mock_yookassa_payment_method_create: MockType,
    ) -> None:
        service.create_payment_method_binding(return_url='https://example.com/callback')
        call_params = mock_yookassa_payment_method_create.call_args[0][0]
        assert call_params['confirmation']['return_url'] == 'https://example.com/callback'

    def test_create_payment_method_binding_falls_back_to_settings_url(
        self,
        service: YookassaPaymentsService,
        mock_yookassa_payment_method_create: MockType,
        settings: SettingsWrapper,
    ) -> None:
        settings.YOOKASSA_RETURN_URL = 'https://settings.example.com/return'
        service.create_payment_method_binding()
        call_params = mock_yookassa_payment_method_create.call_args[0][0]
        assert call_params['confirmation']['return_url'] == 'https://settings.example.com/return'

    def test_create_payment_method_binding_params_structure(
        self,
        service: YookassaPaymentsService,
        mock_yookassa_payment_method_create: MockType,
    ) -> None:
        service.create_payment_method_binding(return_url='https://example.com')
        call_params = mock_yookassa_payment_method_create.call_args[0][0]
        assert call_params['type'] == 'bank_card'
        assert call_params['confirmation']['type'] == 'redirect'

    def test_get_payment_method_calls_find_one(
        self,
        service: YookassaPaymentsService,
        mock_yookassa_payment_method_find_one: MockType,
    ) -> None:
        service.get_payment_method('pm-method-id-456')
        mock_yookassa_payment_method_find_one.assert_called_once_with('pm-method-id-456')
