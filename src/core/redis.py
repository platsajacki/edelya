from django.conf import settings

from redis import Redis

from core.utils import build_redis_retry_policy

retry = build_redis_retry_policy(
    attempts=settings.REDIS_TOTAL_CONNECTION_ATTEMPTS,
    base=settings.REDIS_RETRY_BACKOFF_BASE,
    cap=settings.REDIS_RETRY_BACKOFF_CAP,
)
redis_client = Redis.from_url(
    settings.REDIS_URL,
    retry=retry,
)
