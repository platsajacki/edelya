from typing import TYPE_CHECKING
from uuid import uuid4

from django.db import models

from apps.subscriptions.models.managers.payments import PaymentManager
from apps.subscriptions.models.model_enums import PaymentStatus, PaymentType
from core.base.abstract_models import BaseModel

if TYPE_CHECKING:
    from apps.subscriptions.models import (
        PaymentMethod,  # noqa: F401
        Subscription,  # noqa: F401
    )
    from apps.users.models import User  # noqa: F401


class Payment(BaseModel):
    if TYPE_CHECKING:
        subscription: Subscription
        user: User
        payment_method: PaymentMethod
    subscription = models.ForeignKey(  # type: ignore[assignment]
        'subscriptions.Subscription',
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Подписка',
    )
    user = models.ForeignKey(  # type: ignore[assignment]
        'users.User',
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Плательщик',
    )
    yookassa_payment_id = models.CharField(
        verbose_name='ID платежа в YooKassa',
        max_length=64,
        unique=True,
        null=True,
        blank=True,
    )
    amount = models.DecimalField(
        verbose_name='Сумма',
        max_digits=10,
        decimal_places=2,
    )
    currency = models.CharField(
        verbose_name='Валюта',
        max_length=3,
        default='RUB',
    )
    status = models.CharField(
        verbose_name='Статус',
        max_length=32,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    payment_type = models.CharField(
        verbose_name='Тип платежа',
        max_length=32,
        choices=PaymentType.choices,
    )
    payment_method = models.ForeignKey(  # type: ignore[assignment]
        'subscriptions.PaymentMethod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name='Метод оплаты',
    )
    idempotence_key = models.UUIDField(
        verbose_name='Ключ идемпотентности',
        default=uuid4,
        unique=True,
    )
    paid_at = models.DateTimeField(
        verbose_name='Оплачено в',
        null=True,
        blank=True,
    )
    description = models.TextField(
        verbose_name='Описание',
        null=True,
        blank=True,
    )
    cancellation_reason = models.CharField(
        verbose_name='Причина отмены',
        max_length=255,
        null=True,
        blank=True,
    )
    metadata = models.JSONField(
        verbose_name='Метаданные',
        default=dict,
    )
    send_to_tax3r = models.BooleanField(
        verbose_name='Отправлено в Tax3r',
        default=False,
    )
    is_check_sent = models.BooleanField(
        default=False,
        verbose_name='Отправлен ли чек в налоговую',
        editable=False,
        help_text='Устанавливается в True после успешного получения ответа от Tax3r.',
    )
    check_url = models.URLField(
        verbose_name='URL для проверки чека',
        null=True,
        blank=True,
        editable=False,
    )

    objects: PaymentManager = PaymentManager()

    class Meta:
        verbose_name = 'Платёж'
        verbose_name_plural = 'Платежи'

    def __str__(self) -> str:
        return f'Payment {self.yookassa_payment_id or self.id} [{self.status}]'
