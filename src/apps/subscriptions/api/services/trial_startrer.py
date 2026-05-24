from dataclasses import dataclass
from dataclasses import field as dc_field

from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotFound, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from apps.subscriptions.api.serializers.subscriptions import SubscriptionSerializer
from apps.subscriptions.models import Subscription, Tariff
from apps.subscriptions.models.model_enums import SubscriptionStatus
from apps.users.models import User
from core.base.services import BaseService


@dataclass
class TrialStarter(BaseService):
    request: Request
    serializer_class: type[SubscriptionSerializer]
    authenticated_user: User = dc_field(init=False)

    def _validate_user(self) -> None:
        if not isinstance(self.request.user, User):
            raise AuthenticationFailed('User must be authenticated.')
        self.authenticated_user = self.request.user

    def get_validators(self) -> list:
        return super().get_validators() + [self._validate_user, self._check_trial]

    def _check_trial(self) -> None:
        if hasattr(self.authenticated_user, 'subscription'):
            raise ValidationError('User already has a subscription.')

    def act(self) -> Response:
        try:
            trial_tariff = Tariff.objects.get_trial_tariff()
        except Tariff.DoesNotExist as e:
            raise NotFound('Trial tariff not found.') from e
        subscription = Subscription(
            user=self.authenticated_user,
            tariff=trial_tariff,
            status=SubscriptionStatus.TRIAL,
            trial_started_at=timezone.now(),
            days_in_trial=trial_tariff.trial_days,
        )
        subscription.trial_ended_at = subscription.get_trial_end_date()
        subscription.save()
        serializer = self.serializer_class(subscription)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
