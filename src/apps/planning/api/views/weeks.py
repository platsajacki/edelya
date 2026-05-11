from typing import Any

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.planning.api.schemas import WeekDishesAPIViewSchema
from apps.planning.api.services.week_dishes_getter import WeekDishesGetter
from core.base.decorators import extend_schema_view_from_class
from core.base.permissions import CanUseBaseFeatures, HasActiveTrial
from core.logging_handlers import loki_logger


@extend_schema_view_from_class(WeekDishesAPIViewSchema)
class WeekDishesAPIView(APIView):
    permission_classes = [IsAuthenticated & (HasActiveTrial | CanUseBaseFeatures)]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        inf = {
            'IP META': {
                'REMOTE_ADDR': request.META.get('REMOTE_ADDR'),
                'X_FORWARDED_FOR': request.META.get('HTTP_X_FORWARDED_FOR'),
                'X_REAL_IP': request.META.get('HTTP_X_REAL_IP'),
            },
            'HEADERS': dict(request.headers),
            'USER AGENT': request.headers.get('User-Agent'),
            'META': dict(request.META),
        }
        loki_logger.info(str(inf))
        return WeekDishesGetter(user=request.user, year=kwargs['year'], week=kwargs['week'])()
