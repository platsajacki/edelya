from collections.abc import Iterable

from django.db import models
from django.db.models import Q
from django.db.models.base import ModelBase
from django.db.models.functions import Lower

from app.base.abstract_models import BaseModel
from app.utils import normalize_string
from dishes.models.model_enums import Unit


class IngredientCategory(BaseModel):
    name = models.CharField(
        verbose_name='Название категории',
        max_length=128,
        unique=True,
    )
    slug = models.SlugField(
        verbose_name='Уникальный идентификатор категории',
        max_length=128,
        unique=True,
    )
    is_active = models.BooleanField(
        verbose_name='Активность категории',
        default=True,
    )

    class Meta:
        verbose_name = 'Категория ингредиента'
        verbose_name_plural = 'Категории ингредиентов'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Ingredient(BaseModel):
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ingredients',
        verbose_name='Владелец ингредиента',
        help_text='NULL = системный ингредиент, иначе пользовательский',
    )
    category = models.ForeignKey(
        IngredientCategory,
        on_delete=models.PROTECT,
        related_name='ingredients',
        verbose_name='Категория ингредиента',
    )
    name = models.CharField(
        verbose_name='Название ингредиента',
        max_length=255,
    )
    base_unit = models.CharField(
        verbose_name='Базовая единица измерения',
        max_length=10,
        choices=Unit.choices,
    )
    is_active = models.BooleanField(
        verbose_name='Активность ингредиента',
        default=True,
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                Lower('name'),
                name='unique_ingredient_global',
                condition=Q(owner__isnull=True),
            ),
            models.UniqueConstraint(
                'owner',
                Lower('name'),
                name='unique_ingredient_user',
                condition=Q(owner__isnull=False),
            ),
        ]
        indexes = [
            models.Index(
                fields=['owner', 'name'],
                name='idx_ingredient_owner_name',
                condition=Q(is_active=True),
            ),
        ]

    def save(
        self,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        self.name = normalize_string(self.name)
        return super().save(
            force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields
        )
