from rest_framework.exceptions import APIException


class SubscriptionRequired(APIException):
    status_code = 402
    default_detail = 'Subscription required to access this resource.'
    default_code = 'subscription_required'


class TrialExpired(APIException):
    status_code = 402
    default_detail = 'Trial period has expired. Please subscribe to continue using this resource.'
    default_code = 'trial_expired'


class SubscriptionInactive(APIException):
    status_code = 402
    default_detail = 'Your subscription is inactive. Please check your subscription status.'
    default_code = 'subscription_inactive'


class SubscriptionCancelled(APIException):
    status_code = 402
    default_detail = (
        'Your subscription has been cancelled. Please renew your subscription to continue using this resource.'
    )
    default_code = 'subscription_cancelled'


class SubscriptionPastDue(APIException):
    status_code = 402
    default_detail = (
        'Your subscription payment is past due. Please update your payment information to continue using this resource.'
    )
    default_code = 'subscription_past_due'


class SubscriptionExpired(APIException):
    status_code = 402
    default_detail = 'Your subscription has expired. Please renew your subscription to continue using this resource.'
    default_code = 'subscription_expired'
