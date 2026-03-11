from django.db import models

from apps.planning.models.managers.meal_plan import MealPlanItemManager
from core.base.abstract_models import BaseModel


class MealPlanItem(BaseModel):
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='meal_plan_items',
        verbose_name='Владелец',
    )
    date = models.DateField(
        verbose_name='День',
    )
    dish = models.ForeignKey(
        'dishes.Dish',
        on_delete=models.PROTECT,
        related_name='meal_plan_items',
        verbose_name='Блюдо',
    )
    cooking_event = models.ForeignKey(
        'planning.CookingEvent',
        on_delete=models.CASCADE,
        related_name='meal_plan_items',
        verbose_name='Готовка-источник',
        null=True,
        blank=True,
    )
    position = models.PositiveIntegerField(
        verbose_name='Позиция внутри дня',
        default=100,
    )
    is_manual = models.BooleanField(
        verbose_name='Добавлено вручную',
        default=False,
    )

    objects: MealPlanItemManager = MealPlanItemManager()

    class Meta:
        verbose_name = 'Элемент плана питания'
        verbose_name_plural = 'Элементы плана питания'
        ordering = ['date', 'position', 'created_at']
        indexes = [
            models.Index(
                fields=['owner', 'date'],
                name='idx_meal_owner_date',
            ),
            models.Index(
                fields=['owner', 'date', 'position'],
                name='idx_meal_owner_date_pos',
            ),
            models.Index(
                fields=['cooking_event'],
                name='idx_meal_cooking_event',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'date', 'position'],
                name='unique_meal_position_per_day',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.date}: {self.dish}'
