from datetime import timedelta

BASIC_TARIFF_NAME = 'Basic'
ZERO_AMOUNT_BINDING_EXPIRY = timedelta(hours=24)

###################################################################################
#  WARNING! Do not change the following constants without careful consideration,
#  as they have implications for users and are used in documentation.
###################################################################################
DEFAULT_TRIAL_DAYS = 14
GRACE_PERIOD_DAYS = 7
CHECK_SUBSCRIPTION_PAYMENT_TIMEDELTA = timedelta(minutes=5)
AI_RECIPE_LIMIT_PER_PERIOD = 50
#  END OF WARNING
