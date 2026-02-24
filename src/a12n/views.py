from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response

from rest_framework_simplejwt.views import TokenObtainPairView as JWTObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView as JWTTokenRefreshView

from a12n.schemas import TelegramA12nJWTSchema, TokenRefreshViewSchema
from a12n.services.telegram_a12n_jwt import TelegramA12nJWTService
from app.base.decorators import extend_schema_view_from_class


@extend_schema_view_from_class(TokenRefreshViewSchema)
class TokenRefreshView(JWTTokenRefreshView): ...


class LoginTokenObtainPairView(JWTObtainPairView): ...


@extend_schema_view_from_class(TelegramA12nJWTSchema)
class TelegramTokenObtainPairView(JWTObtainPairView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return TelegramA12nJWTService(request=request)()
