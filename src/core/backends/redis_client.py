from django.conf import settings

from redis import Redis

from core.utils import build_redis_retry_policy

cluster_redis_retry_policy = build_redis_retry_policy(
    attempts=settings.REDIS_TOTAL_CONNECTION_ATTEMPTS,
    base=settings.REDIS_RETRY_BACKOFF_BASE,
    cap=settings.REDIS_RETRY_BACKOFF_CAP,
)
cluster_redis = Redis.from_url(settings.CLUSTER_REDIS_URL, retry=cluster_redis_retry_policy)
