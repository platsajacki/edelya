from collections.abc import Hashable
from typing import Any

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models

from apps.settings.managers import PromptManager
from apps.settings.model_enums import PromptName
from core.base.abstract_models import BaseModel


class SafeFormatDict(dict):
    def __missing__(self, key: Hashable) -> str:
        return f'{{{key}}}'


class Prompt(BaseModel):
    name = models.CharField(
        verbose_name='Название',
        max_length=255,
        choices=PromptName.choices,
        db_index=True,
        unique=True,
    )
    text = models.TextField(
        verbose_name='Текст',
    )
    required_variables = ArrayField(
        models.CharField(max_length=255),
        verbose_name='Обязательные переменные',
        default=list,
        editable=False,
    )

    objects: PromptManager = PromptManager()

    class Meta:
        verbose_name = 'Промпт'
        verbose_name_plural = 'Промпты'

    def __str__(self) -> str:
        return f'Промпт `{self.name}`'

    def save(self, *args: Any, **kwargs: Any) -> None:
        missing_variables = [variable for variable in self.required_variables if f'{{{{{variable}}}}}' not in self.text]
        if missing_variables:
            message = f'Переменные отсутствуют в тексте промпта: {missing_variables}.'
            raise ValidationError({'required_variables': message})
        return super().save(*args, **kwargs)

    def render_text(self, variables: dict) -> str:
        return self.text.format_map(SafeFormatDict(variables))
