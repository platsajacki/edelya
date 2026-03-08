from django.core.validators import MinValueValidator
from django.db import models

from apps.planning.models.managers.cooking import CookingEventManager
from core.base.abstract_models import BaseModel


class CookingEvent(BaseModel):
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='cooking_events',
        verbose_name='Владелец',
    )
    dish = models.ForeignKey(
        'dishes.Dish',
        on_delete=models.PROTECT,
        related_name='cooking_events',
        verbose_name='Блюдо',
    )
    cooking_date = models.DateField(
        verbose_name='День готовки',
    )
    duration_days = models.PositiveSmallIntegerField(
        verbose_name='На сколько дней хватит',
        validators=[MinValueValidator(1)],
    )
    start_eating_date = models.DateField(
        verbose_name='Когда начнем есть',
    )
    notes = models.TextField(
        verbose_name='Комментарий',
        blank=True,
        default='',
    )

    objects: CookingEventManager = CookingEventManager()

    class Meta:
        verbose_name = 'Событие готовки'
        verbose_name_plural = 'События готовки'
        ordering = ['cooking_date', 'created_at']
        indexes = [
            models.Index(
                fields=['owner', 'cooking_date'],
                name='idx_cook_owner_date',
            ),
            models.Index(
                fields=['owner', 'dish'],
                name='idx_cook_owner_dish',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.dish} ({self.cooking_date})'
