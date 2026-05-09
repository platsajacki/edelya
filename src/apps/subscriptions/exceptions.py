from typing import Any
from uuid import UUID

from core.base.exceptions import BaseError


class PaymentError(BaseError): ...


class PaymentPendingRecurringError(PaymentError):
    def __init__(self, subscription_id: str | UUID, message: str | None = None, **context: Any) -> None:
        self.message = message or f'Subscription {subscription_id!r} has a pending recurring payment.'
        self.context = context


class SubscriptionDoesHavePendingTariffError(PaymentError):
    def __init__(self, subscription_id: str | UUID, message: str | None = None, **context: Any) -> None:
        self.message = message or f'Subscription {subscription_id!r} does not have a pending tariff.'
        self.context = context
