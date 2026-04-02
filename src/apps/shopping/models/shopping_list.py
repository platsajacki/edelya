from django.core.validators import MinValueValidator
from django.db import models

from apps.shopping.models.managers.shopping_list import ShoppingListItemManager, ShoppingListManager
from core.base.abstract_models import BaseModel


class ShoppingList(BaseModel):
    name = models.CharField(
        verbose_name='Название списка покупок',
        max_length=255,
    )
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='shopping_lists',
        verbose_name='Владелец списка покупок',
    )
    date_from = models.DateField(
        verbose_name='Начало периода',
    )
    date_to = models.DateField(
        verbose_name='Конец периода',
    )

    objects: ShoppingListManager = ShoppingListManager()

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['owner', 'date_from', 'date_to'],
                name='idx_shop_list_owner_period',
            ),
        ]

    def __str__(self) -> str:
        return self.name


class ShoppingListItem(BaseModel):
    shopping_list = models.ForeignKey(
        'shopping.ShoppingList',
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Список покупок',
    )
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='shopping_list_items',
        verbose_name='Владелец пункта списка покупок',
    )
    ingredient = models.ForeignKey(
        'dishes.Ingredient',
        on_delete=models.PROTECT,
        related_name='shopping_list_items',
        verbose_name='Ингредиент',
    )
    amount = models.DecimalField(
        verbose_name='Количество',
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(0)],
    )
    is_checked = models.BooleanField(
        verbose_name='Куплено',
        default=False,
    )
    checked_at = models.DateTimeField(
        verbose_name='Дата отметки',
        null=True,
        blank=True,
    )
    is_manual = models.BooleanField(
        verbose_name='Добавлено вручную',
        default=False,
    )
    position = models.PositiveIntegerField(
        verbose_name='Позиция',
        default=100,
    )

    objects: ShoppingListItemManager = ShoppingListItemManager()

    class Meta:
        verbose_name = 'Пункт списка покупок'
        verbose_name_plural = 'Пункты списка покупок'
        ordering = ['position', '-created_at']
        indexes = [
            models.Index(
                fields=['owner', 'shopping_list'],
                name='idx_shop_list_item_owner_list',
            ),
        ]
