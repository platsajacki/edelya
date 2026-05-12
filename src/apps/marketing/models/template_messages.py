from typing import Any

from django.db import models

from core.base.abstract_models import BaseModel
from core.base.data_types import SafeFormatDict
from core.base.validators import validate_balanced_braces


class MessageTemplate(BaseModel):
    name = models.CharField(
        verbose_name='Название',
        max_length=255,
        db_index=True,
        unique=True,
    )
    text_str = models.TextField(
        'Текс сообщения',
        max_length=4000,
        validators=[validate_balanced_braces],
        help_text='см. в "Описание переменных"',
    )
    with_variables = models.BooleanField(
        'С переменными',
        default=False,
    )
    variables_description = models.TextField(
        'Описание переменных',
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'Шаблон сообщения'
        verbose_name_plural = 'Шаблоны сообщений'

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.text_str = self.text_str.replace('\r', '')
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'Шаблон сообщения `{self.name}`'

    def render_text_str(self, variables: dict) -> str:
        """
        Рендер шаблона с помощью переданных переменных.
        Если в шаблоне есть переменные, которые не были переданы, они останутся в виде {variable_name}.
        """
        return self.text_str.format_map(SafeFormatDict(variables))
