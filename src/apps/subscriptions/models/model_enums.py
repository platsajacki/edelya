from django.db import models


class SubscriptionStatus(models.TextChoices):
    TRIAL = 'trial', 'Trial'
    ACTIVE = 'active', 'Active'
    PAST_DUE = 'past_due', 'Past Due'
    CANCELLED = 'cancelled', 'Cancelled'
    EXPIRED = 'expired', 'Expired'


class BillingPeriod(models.TextChoices):
    MONTHLY = 'monthly', 'Monthly'
    YEARLY = 'yearly', 'Yearly'


class PaymentStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    WAITING_CAPTURE = 'waiting_for_capture', 'Waiting for Capture'
    SUCCEEDED = 'succeeded', 'Succeeded'
    CANCELED = 'canceled', 'Canceled'


class PaymentType(models.TextChoices):
    FIRST_PAYMENT = 'first_payment', 'First Payment'
    RECURRING = 'recurring', 'Recurring'
    ZERO_AMOUNT_BINDING = 'zero_amount_binding', 'Zero Amount Binding'
