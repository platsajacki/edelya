from django.db import models

from apps.subscriptions.constants import DEFAULT_TRIAL_DAYS
from apps.subscriptions.models.managers import TariffManager
from apps.subscriptions.models.model_enums import BillingPeriod
from core.base.abstract_models import BaseModel


class Tariff(BaseModel):
    name = models.CharField(
        verbose_name='Название',
        max_length=255,
        unique=True,
    )
    price = models.DecimalField(
        verbose_name='Цена',
        max_digits=10,
        decimal_places=2,
    )
    description = models.TextField(
        verbose_name='Описание',
        blank=True,
        null=True,
    )
    billing_period = models.CharField(
        verbose_name='Период оплаты',
        max_length=10,
        choices=BillingPeriod.choices,
        default=BillingPeriod.MONTHLY,
    )
    is_trial_tariff = models.BooleanField(
        verbose_name='Пробный тариф',
        default=False,
    )
    trial_days = models.PositiveIntegerField(
        verbose_name='Дней в пробном периоде',
        default=DEFAULT_TRIAL_DAYS,
    )
    published = models.BooleanField(
        verbose_name='Опубликован',
        default=False,
    )
    is_active = models.BooleanField(
        verbose_name='Активный',
        default=True,
    )
    sort_order = models.PositiveIntegerField(
        verbose_name='Порядок сортировки',
        default=0,
    )
    can_use_base_features = models.BooleanField(
        verbose_name='Может использовать базовые функции',
        default=True,
    )
    can_create_ai_recipes = models.BooleanField(
        verbose_name='Может создавать AI рецепты',
    )

    objects: TariffManager = TariffManager()

    class Meta:
        verbose_name = 'Тариф'
        verbose_name_plural = 'Тарифы'
        ordering = ['sort_order', 'price']
        constraints = [
            models.UniqueConstraint(
                fields=['is_trial_tariff'],
                condition=models.Q(is_trial_tariff=True, is_active=True),
                name='unique_trial_tariff',
            )
        ]

    def __str__(self) -> str:
        return self.name
