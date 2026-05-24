from dataclasses import dataclass

from django.conf import settings
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import RefreshToken

from apps.a12n.validators import TelegramDataValidator, WebAppUserData
from apps.users.api.serializers.users import ConsentSerializer
from apps.users.models import User
from apps.users.models.consents import ConsentLog
from apps.users.models.legal_docs import PrivacyPolicyVersion, TermsOfServiceVersion
from apps.users.models.model_enums import ConsentAction, ConsentType
from core.base.services import BaseService
from core.logging_handlers import loki_logger
from core.utils import get_client_ip

REGISTRATION_CONSENT_TYPES = [
    ConsentType.TERMS_OF_SERVICE,
    ConsentType.PRIVACY_POLICY,
    ConsentType.MARKETING_COMMUNICATIONS,
]


@dataclass
class TelegramA12nJWTService(BaseService):
    request: Request

    def _create_user(self, tg_user: WebAppUserData) -> User:
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
            loki_logger.error(f'Telegram ID {tg_id} already exists.', exc_info=True)
            return User.objects.get(telegram_id=tg_id)

    @transaction.atomic
    def _create_consent_logs(self, user: User, marketing: bool, ip: str | None, ua: str | None) -> None:
        tos_version = TermsOfServiceVersion.objects.current()
        pp_version = PrivacyPolicyVersion.objects.current()
        logs = [
            ConsentLog(
                user=user,
                consent_type=ConsentType.TERMS_OF_SERVICE,
                action=ConsentAction.GRANTED,
                ip_address=ip,
                user_agent=ua,
                terms_of_service_version=tos_version,
            ),
            ConsentLog(
                user=user,
                consent_type=ConsentType.PRIVACY_POLICY,
                action=ConsentAction.GRANTED,
                ip_address=ip,
                user_agent=ua,
                privacy_policy_version=pp_version,
            ),
        ]
        if marketing:
            logs.append(
                ConsentLog(
                    user=user,
                    consent_type=ConsentType.MARKETING_COMMUNICATIONS,
                    action=ConsentAction.GRANTED,
                    ip_address=ip,
                    user_agent=ua,
                )
            )
            user.marketing_communications = True
            user.save(update_fields=['marketing_communications'])
        ConsentLog.objects.bulk_create(logs)

    def _write_consent_logs(self, user: User, marketing: bool) -> None:
        self._create_consent_logs(
            user=user,
            marketing=marketing,
            ip=get_client_ip(self.request),
            ua=self.request.headers.get('User-Agent'),
        )

    def _requires_consent_response(self) -> Response:
        return Response(
            {'requires_consent': True, 'consents': REGISTRATION_CONSENT_TYPES},
            status=status.HTTP_428_PRECONDITION_REQUIRED,
        )

    def _handle_new_user(self, tg_user: WebAppUserData) -> Response:
        consent_serializer = ConsentSerializer(data=self.request.data)
        if not consent_serializer.is_valid():
            return self._requires_consent_response()
        user = self._create_user(tg_user)
        self._write_consent_logs(
            user=user,
            marketing=consent_serializer.validated_data.get('marketing_communications', False),
        )
        return self._token_response(user)

    def _token_response(self, user: User) -> Response:
        refresh = RefreshToken.for_user(user)
        return Response(
            {'refresh': str(refresh), 'access': str(refresh.access_token)},
            status=status.HTTP_200_OK,
        )

    def get_valid_response(self, tg_user: WebAppUserData) -> Response:
        tg_id = tg_user['id']
        try:
            user = User.objects.get(telegram_id=tg_id)
        except User.DoesNotExist:
            return self._handle_new_user(tg_user)
        return self._token_response(user)

    def act(self) -> Response:
        tg_user = TelegramDataValidator(request=self.request, bot_token=settings.EDELYA_BOT_TOKEN)()
        if not tg_user:
            raise AuthenticationFailed('Invalid Telegram data')
        return self.get_valid_response(tg_user)
