import pytest
from pytest_mock import MockFixture, MockType


@pytest.fixture
def mock_tg_validator(mocker: MockFixture, valid_tg_user_data: dict) -> MockType:
    return mocker.patch(
        'apps.a12n.validators.TelegramDataValidator.validate',
        return_value=valid_tg_user_data,
    )
