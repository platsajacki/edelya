import pytest
from pytest_mock import MockFixture, MockType


@pytest.fixture
def mock_tg_validator(mocker: MockFixture, valid_tg_user_data: dict) -> MockType:
    return mocker.patch(
        'apps.a12n.validators.TelegramDataValidator.validate',
        return_value=valid_tg_user_data,
    )


@pytest.fixture
def mock_yookassa_payment_create(mocker: MockFixture) -> MockType:
    return mocker.patch('apps.subscriptions.services.yookassa_payments.YooPayment.create')


@pytest.fixture
def mock_yookassa_payment_find_one(mocker: MockFixture) -> MockType:
    return mocker.patch('apps.subscriptions.services.yookassa_payments.YooPayment.find_one')


@pytest.fixture
def mock_yookassa_payment_capture(mocker: MockFixture) -> MockType:
    return mocker.patch('apps.subscriptions.services.yookassa_payments.YooPayment.capture')


@pytest.fixture
def mock_yookassa_payment_cancel(mocker: MockFixture) -> MockType:
    return mocker.patch('apps.subscriptions.services.yookassa_payments.YooPayment.cancel')


@pytest.fixture
def mock_yookassa_payment_method_create(mocker: MockFixture) -> MockType:
    return mocker.patch('apps.subscriptions.services.yookassa_payments.YooPaymentMethod.create')


@pytest.fixture
def mock_yookassa_payment_method_find_one(mocker: MockFixture) -> MockType:
    return mocker.patch('apps.subscriptions.services.yookassa_payments.YooPaymentMethod.find_one')
