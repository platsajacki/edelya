from django.db import models

from core.base.abstract_models import BaseModel


class PaymentMethod(BaseModel):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='payment_methods',
        verbose_name='Пользователь',
    )
    yookassa_payment_method_id = models.CharField(
        verbose_name='ID способа оплаты в YooKassa',
        max_length=64,
        unique=True,
    )
    payment_method_type = models.CharField(
        verbose_name='Тип метода оплаты',
        max_length=32,
    )
    card_last4 = models.CharField(
        verbose_name='Последние 4 цифры карты',
        max_length=4,
        null=True,
        blank=True,
    )
    card_type = models.CharField(
        verbose_name='Тип карты',
        max_length=32,
        null=True,
        blank=True,
    )
    title = models.CharField(
        verbose_name='Название',
        max_length=128,
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(
        verbose_name='Активен',
        default=True,
    )

    class Meta:
        verbose_name = 'Метод оплаты'
        verbose_name_plural = 'Методы оплаты'

    def __str__(self) -> str:
        return self.title or f'{self.payment_method_type} *{self.card_last4}'
