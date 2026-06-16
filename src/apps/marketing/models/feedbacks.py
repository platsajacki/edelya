from django.db import models

from apps.marketing.models.model_enums import FeedbackRating
from core.base.abstract_models import BaseModel


class Feedback(BaseModel):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='feedbacks',
        verbose_name='Пользователь',
    )
    text = models.TextField(
        verbose_name='Текст отзыва',
        default='',
    )
    rating = models.IntegerField(
        choices=FeedbackRating.choices,
        verbose_name='Оценка',
    )

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
