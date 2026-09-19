from logging import Handler, LogRecord, getLogger
from os import getenv

from telebot import TeleBot, apihelper
from telebot.util import antiflood

TELEGRAM_PROXY = getenv('TELEGRAM_PROXY', '')
if TELEGRAM_PROXY:
    apihelper.proxy = {'https': TELEGRAM_PROXY, 'http': TELEGRAM_PROXY}  # type: ignore[assignment]

logger_tg_token = getenv('LOGGER_TELEGRAM_TOKEN', '')
bot = TeleBot(logger_tg_token) if logger_tg_token else None

ERROR_CHAT_ID = getenv('LOGGER_ERROR_CHAT_ID', '')
MAX_MESSAGE_LENGTH = 4096

app_logger = getLogger('app')
tg_logger = getLogger('tg')


class TelegramHandler(Handler):
    def __init__(self) -> None:
        super().__init__()
        self.bot = bot
        self.chat_id = ERROR_CHAT_ID
        self.MAX_MESSAGE_LENGTH = MAX_MESSAGE_LENGTH

    def emit(self, record: LogRecord) -> None:
        if not self.bot or not self.chat_id:
            app_logger.error(f'Telegram logging is not configured properly. Bot: {self.bot}, Chat ID: {self.chat_id}')
            return
        try:
            log_entry = self.format(record)
            for i in range(0, len(log_entry), self.MAX_MESSAGE_LENGTH):
                antiflood(
                    self.bot.send_message,
                    self.chat_id,
                    log_entry[i : i + self.MAX_MESSAGE_LENGTH],
                )
        except Exception as e:
            app_logger.error(f'Failed to send log to Telegram: {e}\nOriginal log: {self.format(record)}')


def get_logging_dict(log_formatter: str, datetime_formatter: str, debug: bool) -> dict:
    logging_dict = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'main': {
                'format': log_formatter,
                'datefmt': datetime_formatter,
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'main',
            },
            'telegram_error': {
                'level': 'DEBUG',
                'class': 'core.logging_handlers.TelegramHandler',
                'formatter': 'main',
            },
        },
        'loggers': {
            'app': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            'django': {
                'handlers': ['console', 'telegram_error'],
                'level': 'ERROR',
                'propagate': False,
            },
            'tg': {
                'handlers': ['console', 'telegram_error'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'celery': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
        },
    }
    if debug:
        for logger in logging_dict['loggers'].values():  # type: ignore[attr-defined]
            logger['handlers'] = ['console']
    return logging_dict
