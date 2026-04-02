from collections.abc import Iterable

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.base import ModelBase
from django.db.models.functions import Lower

from apps.dishes.models.managers.dishes import DishCategoryManager, DishIngredientManager, DishManager
from core.base.abstract_models import BaseActiveModel, BaseModel
from core.utils import normalize_string


class DishCategory(BaseActiveModel):
    name = models.CharField(
        verbose_name='Название категории',
        max_length=128,
        unique=True,
    )
    is_active = models.BooleanField(
        verbose_name='Активность категории',
        default=True,
    )

    objects: DishCategoryManager = DishCategoryManager()

    class Meta:
        verbose_name = 'Категория блюда'
        verbose_name_plural = 'Категории блюд'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Dish(BaseActiveModel):
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='dishes',
        verbose_name='Владелец блюда',
        help_text='NULL = системное блюдо, иначе пользовательское',
    )
    category = models.ForeignKey(
        DishCategory,
        on_delete=models.PROTECT,
        related_name='dishes',
        verbose_name='Категория блюда',
    )
    name = models.CharField(
        verbose_name='Название блюда',
        max_length=255,
    )
    recipe = models.TextField(
        verbose_name='Рецепт',
        blank=True,
        default='',
    )
    is_active = models.BooleanField(
        verbose_name='Активность блюда',
        default=True,
    )

    objects: DishManager = DishManager()

    class Meta:
        verbose_name = 'Блюдо'
        verbose_name_plural = 'Блюда'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                Lower('name'),
                name='unique_dish_global',
                condition=Q(owner__isnull=True),
            ),
            models.UniqueConstraint(
                'owner',
                Lower('name'),
                name='unique_dish_user',
                condition=Q(owner__isnull=False),
            ),
        ]
        indexes = [
            models.Index(
                fields=['owner', 'name'],
                name='idx_dish_owner_name',
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
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    def __str__(self) -> str:
        return self.name


class DishIngredient(BaseModel):
    dish = models.ForeignKey(
        'Dish',
        on_delete=models.CASCADE,
        related_name='dish_ingredients',
        verbose_name='Блюдо',
    )
    ingredient = models.ForeignKey(
        'Ingredient',
        on_delete=models.PROTECT,
        related_name='dish_ingredients',
        verbose_name='Ингредиент',
    )
    is_optional = models.BooleanField(
        verbose_name='Опциональность ингредиента',
        default=False,
    )
    amount = models.DecimalField(
        verbose_name='Количество',
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(0)],
    )
    position = models.PositiveIntegerField(
        verbose_name='Позиция',
        default=100,
    )

    objects: DishIngredientManager = DishIngredientManager()

    class Meta:
        verbose_name = 'Ингредиент в блюде'
        verbose_name_plural = 'Ингредиенты в блюде'
        ordering = ['dish', 'position', 'created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['dish', 'ingredient'],
                name='unique_ingredient_per_dish',
            ),
        ]
        indexes = [
            models.Index(
                fields=['dish'],
                name='idx_dish_ingredient_dish',
            ),
            models.Index(
                fields=['ingredient'],
                name='idx_dish_ingredient_ingredient',
            ),
        ]
