from dataclasses import dataclass
from dataclasses import field as dc_field

from django.db.models import QuerySet
from rest_framework.exceptions import AuthenticationFailed, NotFound
from rest_framework.request import Request

from apps.subscriptions.models import Subscription
from apps.users.models import User
from core.base.services import BaseService


@dataclass
class AuthenticatedUserService(BaseService):
    request: Request
    authenticated_user: User = dc_field(init=False)

    def _validate_user(self) -> None:
        if not isinstance(self.request.user, User):
            raise AuthenticationFailed('User must be authenticated.')
        self.authenticated_user = self.request.user

    def get_validators(self) -> list:
        return super().get_validators() + [self._validate_user]


@dataclass
class CurrentSubscriptionService(AuthenticatedUserService):
    subscription: Subscription = dc_field(init=False)

    def get_subscription_queryset(self) -> QuerySet[Subscription]:
        return Subscription.objects.with_tariff()

    def _validate_subscription(self) -> None:
        try:
            self.subscription = self.get_subscription_queryset().get(user=self.authenticated_user)
        except Subscription.DoesNotExist as e:
            raise NotFound('No subscription found.') from e

    def get_validators(self) -> list:
        return super().get_validators() + [self._validate_subscription]
