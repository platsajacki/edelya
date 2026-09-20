from typing import Any

from django.db import connections
from django.http import HttpRequest, JsonResponse
from django.views import View
from rest_framework import status

from core.logging_handlers import app_logger
from core.redis import health_redis


class HealthView(View):
    http_method_names = ['get', 'head']

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        checks = {'db': self.check_db(), 'redis': self.check_redis()}
        _status = status.HTTP_200_OK if all(checks.values()) else status.HTTP_503_SERVICE_UNAVAILABLE
        return JsonResponse(checks, status=_status)

    def check_db(self) -> bool:
        try:
            with connections['default'].cursor() as cursor:
                cursor.execute('SELECT 1')
        except Exception as e:
            app_logger.error(f'Health check failed on db: {e}')
            return False
        return True

    def check_redis(self) -> bool:
        try:
            return bool(health_redis.ping())
        except Exception as e:
            app_logger.error(f'Health check failed on redis: {e}')
            return False
