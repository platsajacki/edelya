from django.conf import settings

from limits.storage import RedisStorage
from limits.strategies import FixedWindowRateLimiter

storage = RedisStorage(settings.TELEGRAM_REDIS_LIMITER_URL)

limiter = FixedWindowRateLimiter(storage)
