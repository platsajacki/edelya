from typing import Any

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.planning.api.schemas import WeekDishesAPIViewSchema
from apps.planning.api.services.week_dishes_getter import WeekDishesGetter
from core.base.decorators import extend_schema_view_from_class
from core.base.permissions import CanUseBaseFeatures, HasActiveTrial


@extend_schema_view_from_class(WeekDishesAPIViewSchema)
class WeekDishesAPIView(APIView):
    permission_classes = [IsAuthenticated & (HasActiveTrial | CanUseBaseFeatures)]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return WeekDishesGetter(user=request.user, year=kwargs['year'], week=kwargs['week'])()
