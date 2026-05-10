from django.db import models


class ConsentType(models.TextChoices):
    TERMS_OF_SERVICE = 'terms_of_service', 'Terms of Service'
    PRIVACY_POLICY = 'privacy_policy', 'Privacy Policy'
    MARKETING_COMMUNICATIONS = 'marketing_communications', 'Marketing Communications'
    PAYMENT_METHOD_STORAGE = 'payment_method_storage', 'Payment Method Storage'
    RECURRING_PAYMENTS = 'recurring_payments', 'Recurring Payments'


class ConsentAction(models.TextChoices):
    GRANTED = 'granted'
    REVOKED = 'revoked'
