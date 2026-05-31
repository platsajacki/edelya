from datetime import datetime
from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException


class BaseError(Exception):
    def __init__(self, message: str | None = None, **context: Any) -> None:
        self.message = message or 'An error occurred during processing.'
        self.context = context

    def _get_formatted_context(self) -> str:
        if not self.context:
            return ''
        context_str = ', '.join(f'{key}={value!r}' for key, value in self.context.items())
        return f' Context: {context_str}'

    def __str__(self) -> str:
        return f'{self.message}{self._get_formatted_context()}'


class ConflictError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Request conflicts with the current resource state.'
    default_code = 'conflict'


class AIRecipeLimitExceeded(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'AI recipe limit for the current subscription period has been exceeded.'
    default_code = 'ai_recipe_limit_exceeded'

    def __init__(self, reset_at: datetime | None) -> None:
        super().__init__(
            detail={
                'detail': self.default_detail,
                'code': self.default_code,
                'reset_at': reset_at.isoformat() if reset_at is not None else None,
            }
        )


class SubscriptionRequired(APIException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = 'Subscription required to access this resource.'
    default_code = 'subscription_required'


class TrialExpired(APIException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = 'Trial period has expired. Please subscribe to continue using this resource.'
    default_code = 'trial_expired'


class SubscriptionInactive(APIException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = 'Your subscription is inactive. Please check your subscription status.'
    default_code = 'subscription_inactive'


class SubscriptionCancelled(APIException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = (
        'Your subscription has been cancelled. Please renew your subscription to continue using this resource.'
    )
    default_code = 'subscription_cancelled'


class SubscriptionPastDue(APIException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = (
        'Your subscription payment is past due. Please update your payment information to continue using this resource.'
    )
    default_code = 'subscription_past_due'


class SubscriptionExpired(APIException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = 'Your subscription has expired. Please renew your subscription to continue using this resource.'
    default_code = 'subscription_expired'
