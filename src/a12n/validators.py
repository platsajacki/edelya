import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import TypedDict
from urllib.parse import parse_qs

from rest_framework.request import Request


class WebAppUserData(TypedDict, total=False):
    id: int
    is_bot: bool | None
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None
    is_premium: bool | None
    added_to_attachment_menu: bool | None
    allows_write_to_pm: bool | None
    photo_url: str | None


@dataclass
class TelegramDataValidator:
    request: Request
    bot_token: str

    def get_secret_key(self) -> bytes:
        return hmac.new(
            key=b'WebAppData',
            msg=self.bot_token.encode(),
            digestmod=hashlib.sha256,
        ).digest()

    def calculate_hash(self, data_string: str) -> str:
        return hmac.new(
            key=self.get_secret_key(),
            msg=data_string.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()

    def validate(self) -> WebAppUserData | None:
        tg_init_data = self.request.headers.get('X-TG-INIT-DATA')
        if not tg_init_data:
            return None
        data = parse_qs(tg_init_data)
        received_hash = data.pop('hash', [None])[0]
        if not received_hash:
            return None
        data_check_string = '\n'.join(
            [f'{k}={v[0]}' for k, v in sorted(data.items())],
        )
        calculated_hash = self.calculate_hash(data_check_string)
        if calculated_hash != received_hash:
            return None
        user_data_str = data.get('user', ['null'])[0]
        return json.loads(user_data_str)

    def __call__(self) -> WebAppUserData | None:
        return self.validate()
