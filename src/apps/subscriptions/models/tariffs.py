from django.db import models

from apps.subscriptions.models.managers import TariffManager
from apps.subscriptions.models.model_enums import BillingPeriod
from core.base.abstract_models import BaseModel


class Tariff(BaseModel):
    name = models.CharField(
        verbose_name='Tariff Name',
        max_length=255,
        unique=True,
    )
    price = models.DecimalField(
        verbose_name='Price',
        max_digits=10,
        decimal_places=2,
    )
    description = models.TextField(
        verbose_name='Description',
        blank=True,
        null=True,
    )
    billing_period = models.CharField(
        verbose_name='Billing Period',
        max_length=10,
        choices=BillingPeriod.choices,
        default=BillingPeriod.MONTHLY,
    )
    published = models.BooleanField(
        verbose_name='Published',
        default=False,
    )
    is_active = models.BooleanField(
        verbose_name='Is Active',
        default=True,
    )
    sort_order = models.PositiveIntegerField(
        verbose_name='Sort Order',
        default=0,
    )
    can_use_base_features = models.BooleanField(
        verbose_name='Can Use Base Features',
        default=True,
    )
    can_create_ai_recipes = models.BooleanField(
        verbose_name='Can Create AI Recipes',
    )

    objects: TariffManager = TariffManager()

    class Meta:
        verbose_name = 'Tariff'
        verbose_name_plural = 'Tariffs'
        ordering = ['sort_order', 'price']

    def __str__(self) -> str:
        return self.name
