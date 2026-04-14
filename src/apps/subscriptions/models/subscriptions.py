from datetime import datetime, timedelta

from django.db import models
from django.utils import timezone

from apps.subscriptions.constants import DEFAULT_TRIAL_DAYS
from apps.subscriptions.models.managers import SubscriptionManager
from apps.subscriptions.models.model_enums import SubscriptionStatus
from core.base.abstract_models import BaseModel


class Subscription(BaseModel):
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='subscription',
        verbose_name='Пользователь',
    )
    tariff = models.ForeignKey(
        'subscriptions.Tariff',
        on_delete=models.PROTECT,
        related_name='subscriptions',
        verbose_name='Тариф',
    )
    status = models.CharField(
        verbose_name='Статус',
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.TRIAL,
    )
    trial_started_at = models.DateTimeField(
        verbose_name='Пробный период начался в',
        null=True,
        blank=True,
    )
    days_in_trial = models.PositiveIntegerField(
        verbose_name='Дней в пробном периоде',
        default=DEFAULT_TRIAL_DAYS,
    )
    trial_ended_at = models.DateTimeField(
        verbose_name='Пробный период закончился в',
        null=True,
        blank=True,
    )
    current_period_start = models.DateTimeField(
        verbose_name='Текущий период начался в',
        null=True,
        blank=True,
    )
    current_period_end = models.DateTimeField(
        verbose_name='Текущий период закончился в',
        null=True,
        blank=True,
    )
    auto_renew = models.BooleanField(
        verbose_name='Автопродление',
        default=True,
    )
    cancelled_at = models.DateTimeField(
        verbose_name='Отменено в',
        null=True,
        blank=True,
    )
    pending_tariff = models.ForeignKey(
        'subscriptions.Tariff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pending_subscriptions',
        verbose_name='Ожидающий тариф',
    )
    payment_method = models.ForeignKey(
        'subscriptions.PaymentMethod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subscriptions',
        verbose_name='Метод оплаты',
    )

    objects: SubscriptionManager = SubscriptionManager()

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self) -> str:
        return f'{self.user} — {self.status}'

    def get_trial_end_date(self) -> datetime:
        if self.trial_ended_at is not None:
            return self.trial_ended_at
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
