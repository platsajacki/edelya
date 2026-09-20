from django.conf import settings

from redis import Redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from core.utils import build_redis_retry_policy

HEALTH_REDIS_TIMEOUT = 1
HEALTH_REDIS_RETRIES = 1

retry = build_redis_retry_policy(
    attempts=settings.REDIS_TOTAL_CONNECTION_ATTEMPTS,
    base=settings.REDIS_RETRY_BACKOFF_BASE,
    cap=settings.REDIS_RETRY_BACKOFF_CAP,
)
redis_client = Redis.from_url(
    settings.REDIS_URL,
    retry=retry,
)
health_redis = Redis.from_url(
    settings.REDIS_URL,
    retry=Retry(NoBackoff(), retries=HEALTH_REDIS_RETRIES),
    socket_connect_timeout=HEALTH_REDIS_TIMEOUT,
    socket_timeout=HEALTH_REDIS_TIMEOUT,
)
