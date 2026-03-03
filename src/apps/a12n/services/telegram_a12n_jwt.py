from dataclasses import dataclass

from django.conf import settings
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import RefreshToken

from apps.a12n.validators import TelegramDataValidator, WebAppUserData
from apps.users.models import User
from core.base.services import BaseService
from core.logging_handlers import loki_logger


@dataclass
class TelegramA12nJWTService(BaseService):
    request: Request

    def get_or_create_user(self, tg_user: WebAppUserData) -> User:
        tg_id = tg_user['id']
        try:
            with transaction.atomic():
                user, _ = User.objects.get_or_create(
                    telegram_id=tg_id,
                    defaults={
                        'telegram_name': tg_user.get('first_name', ''),
                        'telegram_username': tg_user.get('username', ''),
                    },
                )
            return user
        except IntegrityError:
            msg = f'Telegram ID {tg_id} already exists.'
            loki_logger.error(msg, exc_info=True)
            return User.objects.get(telegram_id=tg_id)

    def get_valid_response(self, tg_user: WebAppUserData) -> Response:
        user = self.get_or_create_user(tg_user)
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
        )

    def act(self) -> None:
        tg_user = TelegramDataValidator(request=self.request, bot_token=settings.EDELYA_BOT_TOKEN)()
        if not tg_user:
            raise AuthenticationFailed('Invalid Telegram data')
        return self.get_valid_response(tg_user)
