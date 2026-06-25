from __future__ import annotations

from django.db import models

from apps.dishes.data_types import DishPayloadData
from apps.dishes.models.managers.ai_drafts import DishAIDraftManager
from apps.dishes.models.model_enums import DishAIDraftStatus
from apps.dishes.models.validators import DishPayloadValidator
from core.base.abstract_models import BaseModel


class DishAIDraft(BaseModel):
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='dish_ai_drafts',
        verbose_name='Владелец',
    )
    source_text = models.TextField(
        verbose_name='Исходный текст рецепта',
    )
    status = models.CharField(
        verbose_name='Статус',
        max_length=32,
        choices=DishAIDraftStatus.choices,
        default=DishAIDraftStatus.PROCESSING,
    )
    ai_raw_response = models.JSONField(
        verbose_name='Сырой ответ AI',
        null=True,
        blank=True,
    )
    payload = models.JSONField(
        verbose_name='Payload формы создания блюда',
        null=True,
        blank=True,
        validators=[DishPayloadValidator()],
    )
    validation_errors = models.JSONField(
        verbose_name='Ошибки валидации',
        default=list,
        blank=True,
    )
    usage = models.JSONField(
        verbose_name='OpenAI usage',
        null=True,
        blank=True,
    )
    created_dish = models.ForeignKey(
        'dishes.Dish',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_drafts',
        verbose_name='Созданное блюдо',
    )

    objects: DishAIDraftManager = DishAIDraftManager()

    class Meta:
        verbose_name = 'AI-черновик блюда'
        verbose_name_plural = 'AI-черновики блюд'
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['owner', 'status'],
                name='idx_ai_draft_owner_status',
            ),
            models.Index(
                fields=['owner', 'created_at'],
                name='idx_ai_draft_owner_created',
            ),
        ]

    def __str__(self) -> str:
        return f'AI Draft #{self.id} - Status: {self.status}'

    def set_validation_error(self, error_code: str, error_message: str, save: bool = True) -> None:
        error = {
            'error_code': error_code,
            'error_message': error_message,
        }
        self.validation_errors = (self.validation_errors or []) + [error]
        if save:
            self.save(update_fields=['validation_errors'])

    @property
    def payload_data(self) -> DishPayloadData | None:
        if self.payload is None:
            return None
        return DishPayloadData(**self.payload)  # type: ignore[typeddict-item]
