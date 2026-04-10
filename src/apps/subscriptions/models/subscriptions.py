from datetime import datetime, timedelta

from django.db import models
from django.utils import timezone

from apps.subscriptions.models.model_enums import SubscriptionStatus
from core.base.abstract_models import BaseModel


class Subscription(BaseModel):
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='subscription',
        verbose_name='User',
    )
    tariff = models.ForeignKey(
        'subscriptions.Tariff',
        on_delete=models.PROTECT,
        related_name='subscriptions',
        verbose_name='Tariff',
    )
    status = models.CharField(
        verbose_name='Status',
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.TRIAL,
    )
    trial_started_at = models.DateTimeField(
        verbose_name='Trial Started At',
        null=True,
        blank=True,
    )
    days_in_trial = models.PositiveIntegerField(
        verbose_name='Days in Trial',
        default=14,
    )
    trial_ended_at = models.DateTimeField(
        verbose_name='Trial Ended At',
        null=True,
        blank=True,
    )
    current_period_start = models.DateTimeField(
        verbose_name='Current Period Start',
        null=True,
        blank=True,
    )
    current_period_end = models.DateTimeField(
        verbose_name='Current Period End',
        null=True,
        blank=True,
    )
    auto_renew = models.BooleanField(
        verbose_name='Auto Renew',
        default=True,
    )
    cancelled_at = models.DateTimeField(
        verbose_name='Cancelled At',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'

    def __str__(self) -> str:
        return f'{self.user} — {self.status}'

    def get_trial_end_date(self) -> datetime:
        if self.trial_started_at is None:
            return timezone.now() + timedelta(days=self.days_in_trial)
        return self.trial_started_at + timedelta(days=self.days_in_trial)

    @property
    def is_active(self) -> bool:
        now = timezone.now()
        if self.status == SubscriptionStatus.TRIAL:
            return now <= self.get_trial_end_date()
        if self.status == SubscriptionStatus.ACTIVE:
            if self.current_period_end is None:
                return False
            return now <= self.current_period_end
        return False

    @property
    def is_trial_expired(self) -> bool:
        now = timezone.now()
        if self.status != SubscriptionStatus.TRIAL:
            return False
        if self.trial_ended_at and self.trial_ended_at <= now:
            return True
        return self.get_trial_end_date() <= now
