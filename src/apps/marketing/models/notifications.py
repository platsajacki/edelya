from django.db import models

from apps.marketing.models.template_messages import MessageTemplate
from apps.users.models.users import User
from core.base.abstract_models import BaseModel


class Notification(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name='Пользователь',
        related_name='notifications',
        editable=False,
    )
    template = models.ForeignKey(
        MessageTemplate,
        on_delete=models.PROTECT,
        verbose_name='Шаблон уведомления',
        related_name='notifications',
        editable=False,
    )
    delivered = models.BooleanField(
        verbose_name='Доставлено',
        default=True,
        editable=False,
    )
    delivered_at = models.DateTimeField(
        verbose_name='Дата и время доставки',
        null=True,
        blank=True,
        editable=False,
    )
    text_str = models.TextField(
        verbose_name='Текст сообщения (текстовая версия)',
        help_text='Текстовая версия сообщения, отправленного пользователю.',
        editable=False,
    )
    error_message = models.TextField(
        'Текст ошибки',
        default='',
        blank=True,
        editable=False,
    )

    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
