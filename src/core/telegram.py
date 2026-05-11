import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

from django.conf import settings
from rest_framework import status

from limits import RateLimitItemPerSecond
from telebot import TeleBot
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InputFile, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telebot.util import antiflood

from core.base.services import BaseService
from core.logging_handlers import loki_logger
from core.rate_limits import limiter

if TYPE_CHECKING:
    from apps.users.models.users import User

edelya_bot = TeleBot(settings.EDELYA_BOT_TOKEN)
TGKeyboard = Union[InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, None]  # noqa: UP007
edelya_rate_limit = RateLimitItemPerSecond(29, namespace='tg_total_edelya_bot_limiter')


@dataclass
class EdelyaBotSender(BaseService):
    user: User
    text: str
    kb: TGKeyboard = None
    parse_mode: str | None = None
    photo_url: str | None = None
    photo_file_id: str | None = None
    video_url: str | None = None
    video_file_id: str | None = None
    document: str | InputFile | None = None
    anti_flood: bool = False
    with_limit: bool = True

    def handle_400(self, e: ApiTelegramException) -> None:
        loki_logger.warning(self.get_log_msg(f'User {self.user.id} Telegram bad request: {str(e)}'))

    def handle_403(self, e: ApiTelegramException) -> None:
        loki_logger.warning(self.get_log_msg(f'User {self.user.id} Telegram access forbidden: {str(e)}'))
        self.user.inactivate_telegram()
        loki_logger.info(self.get_log_msg(f'User {self.user.id} Telegram inactivated due to 403 error'))

    def handle_429(self, e: ApiTelegramException) -> None:
        loki_logger.warning(self.get_log_msg(f'User {self.user.id} hit Telegram rate limit: {str(e)}'))

    def handle_error(self, e: ApiTelegramException) -> None:
        match e.error_code:
            case status.HTTP_400_BAD_REQUEST:
                self.handle_400(e)
            case status.HTTP_403_FORBIDDEN:
                self.handle_403(e)
            case status.HTTP_429_TOO_MANY_REQUESTS:
                self.handle_429(e)

    def create_kwargs_for_telegram(self, bot: TeleBot, chat_id: str) -> dict:
        kwargs: dict = dict(
            chat_id=chat_id,
            reply_markup=self.kb,
            parse_mode=self.parse_mode,
        )
        if self.video_url or self.video_file_id:
            kwargs['function'] = bot.send_video
            kwargs['video'] = self.video_file_id or self.video_url
            kwargs['caption'] = self.text
        elif self.photo_url or self.photo_file_id:
            kwargs['function'] = bot.send_photo
            kwargs['photo'] = self.photo_file_id or self.photo_url
            kwargs['caption'] = self.text
        elif self.document:
            kwargs['function'] = bot.send_document
            kwargs['document'] = self.document
            kwargs['caption'] = self.text
        else:
            kwargs['function'] = bot.send_message
            kwargs['text'] = self.text
        return kwargs

    def _send_message(self, bot: TeleBot, chat_id: str) -> None:
        kwargs = self.create_kwargs_for_telegram(bot, chat_id)
        if self.anti_flood:
            antiflood(**kwargs)
            return
        func = kwargs.pop('function', bot.send_message)
        if callable(func):
            func(**kwargs)
        else:
            raise ValueError('No valid Telegram function to call')

    def send_message(self, bot: TeleBot, chat_id: str) -> None:
        while self.with_limit and not limiter.hit(edelya_rate_limit):
            window = limiter.get_window_stats(edelya_rate_limit)
            now = time.time()
            sleep_seconds = max(0.0, window.reset_time - now)
            if sleep_seconds <= 0.0:
                time.sleep(0.1)
                continue
            time.sleep(sleep_seconds + 0.01)
        self._send_message(bot, chat_id)

    def act(self) -> bool:
        try:
            if not self.user.telegram_id:
                loki_logger.warning(
                    self.get_log_msg(f'User {self.user.id} does not have a Telegram ID, skipping message sending')
                )
                return False
            self.send_message(edelya_bot, self.user.telegram_id)
            return True
        except ApiTelegramException as e:
            self.handle_error(e)
            return False
