import pytest

import hashlib
import hmac
import json
from urllib.parse import quote_plus

from django.conf import settings
from rest_framework.test import APIClient

from apps.a12n.validators import WebAppUserData
from apps.users.models import User


@pytest.fixture
def telegram_user_data() -> dict:
    return {
        'id': 123456789,
        'first_name': 'Test User',
        'username': 'testuser',
    }


@pytest.fixture
def telegram_user(telegram_user_data: dict) -> User:
    return User.objects.create(
        telegram_id=telegram_user_data['id'],
        telegram_name=telegram_user_data['first_name'],
        telegram_username=telegram_user_data['username'],
    )


@pytest.fixture
def another_telegram_user(telegram_user_data: dict) -> User:
    return User.objects.create(
        telegram_id=telegram_user_data['id'] + 1,
        telegram_name=telegram_user_data['first_name'] + '2',
        telegram_username=telegram_user_data['username'] + '2',
    )


@pytest.fixture
def valid_tg_user_data(telegram_user: User) -> WebAppUserData:
    assert telegram_user.telegram_id is not None
    assert telegram_user.telegram_name is not None
    assert telegram_user.telegram_username is not None
    return WebAppUserData(
        id=int(telegram_user.telegram_id),
        first_name=telegram_user.telegram_name,
        last_name='test',
        username=telegram_user.telegram_username,
        language_code='ru',
        is_premium=False,
        allows_write_to_pm=True,
    )


@pytest.fixture
def valid_tg_data(valid_tg_user_data: WebAppUserData) -> dict:
    user_json = json.dumps(valid_tg_user_data)
    user_encoded = quote_plus(user_json)
    auth_date = '1651234567'
    data_string = f'user={user_encoded}&auth_date={auth_date}'
    secret_key = hmac.new(b'WebAppData', settings.EDELYA_BOT_TOKEN.encode(), hashlib.sha256).digest()
    hash_ = hmac.new(secret_key, data_string.encode(), hashlib.sha256).hexdigest()
    return {'user': user_encoded, 'auth_date': auth_date, 'hash': hash_}


@pytest.fixture
def auth_telegram_api_client(api_client: APIClient, telegram_user: User) -> APIClient:
    api_client.force_authenticate(user=telegram_user)
    return api_client


@pytest.fixture
def auth_another_telegram_api_client(another_telegram_user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=another_telegram_user)
    return client
