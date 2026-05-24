from typing import TYPE_CHECKING
from uuid import UUID

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import Token
from rest_framework_simplejwt.utils import get_md5_hash_password

from apps.subscriptions.models.model_enums import SubscriptionStatus
from core.base.exceptions import (
    SubscriptionCancelled,
    SubscriptionExpired,
    SubscriptionInactive,
    SubscriptionPastDue,
    SubscriptionRequired,
    TrialExpired,
)

if TYPE_CHECKING:
    from apps.users.models import User


class BaseAuthentication:
    user_model: type[User]

    def _get_user(self, user_id: str | UUID) -> User:
        if hasattr(self.user_model.objects, 'with_subscription_and_tariff'):
            return self.user_model.objects.with_subscription_and_tariff().get(**{api_settings.USER_ID_FIELD: user_id})
        return self.user_model.objects.get(**{api_settings.USER_ID_FIELD: user_id})

    def check_subscription(self, user: User) -> None:
        subscription = getattr(user, 'subscription', None)
        if subscription is None:
            raise SubscriptionRequired()
        status = subscription.status
        if status == SubscriptionStatus.TRIAL:
            if subscription.is_trial_expired:
                raise TrialExpired()
        elif status == SubscriptionStatus.ACTIVE:
            if not subscription.is_active:
                raise SubscriptionExpired()
        elif status == SubscriptionStatus.PAST_DUE:
            raise SubscriptionPastDue()
        elif status == SubscriptionStatus.CANCELLED:
            raise SubscriptionCancelled()
        elif status == SubscriptionStatus.EXPIRED:
            raise SubscriptionExpired()
        else:
            raise SubscriptionInactive()


class JWTAuthenticationWithSubscription(BaseAuthentication, JWTAuthentication):
    def get_user(self, validated_token: Token) -> User:  # type: ignore[override]
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError as e:
            raise InvalidToken('Token contained no recognizable user identification') from e
        try:
            user = self._get_user(user_id)
        except self.user_model.DoesNotExist as e:
            raise AuthenticationFailed('User not found', code='user_not_found') from e
        if api_settings.CHECK_USER_IS_ACTIVE and not user.is_active:
            raise AuthenticationFailed('User is inactive', code='user_inactive')
        if api_settings.CHECK_REVOKE_TOKEN and (
            validated_token.get(api_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(user.password)
        ):
            raise AuthenticationFailed("The user's password has been changed.", code='password_changed')
        self.check_subscription(user)
        return user
