from dataclasses import dataclass
from dataclasses import field as dc_field

from rest_framework.exceptions import AuthenticationFailed, NotFound
from rest_framework.request import Request
from rest_framework.response import Response

from apps.subscriptions.api.serializers.subscriptions import SubscriptionSerializer
from apps.subscriptions.models import Subscription
from apps.users.models import User
from core.base.services import BaseService


@dataclass
class SubscriptionGetter(BaseService):
    request: Request
    serializer_class: type[SubscriptionSerializer]
    authenticated_user: User = dc_field(init=False)

    def _validate_user(self) -> None:
        if not isinstance(self.request.user, User) and self.request.user.is_authenticated:
            raise AuthenticationFailed('User must be authenticated.')
        self.authenticated_user = self.request.user

    def get_validators(self) -> list:
        return super().get_validators() + [self._validate_user]

    def act(self) -> Response:
        try:
            subscription = Subscription.objects.with_tariff().get(user=self.authenticated_user)
        except Subscription.DoesNotExist as e:
            raise NotFound('No subscription found.') from e
        serializer = self.serializer_class(subscription)
        return Response(serializer.data)
