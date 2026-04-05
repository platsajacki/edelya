from typing import Any

from rest_framework.exceptions import ValidationError
from rest_framework.fields import HiddenField
from rest_framework.serializers import CurrentUserDefault, ModelSerializer, UUIDField

from apps.dishes.api.serializers.ingredients import IngredientSerializer
from apps.dishes.models import Ingredient
from apps.shopping.constants import MAX_DAYS_TO_SHOPPING_LIST
from apps.shopping.models import ShoppingList, ShoppingListItem
from apps.users.models import User
from core.base.serialisers import CurrentShoppingList


class ShoppingListSerializer(ModelSerializer):
    owner = HiddenField(default=CurrentUserDefault())

    class Meta:
        model = ShoppingList
        fields = [
            'id',
            'name',
            'date_from',
            'date_to',
            'owner',
            'created_at',
            'updated_at',
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        date_from = attrs.get('date_from')
        date_to = attrs.get('date_to')
        if date_from and date_to and date_from > date_to:
            raise ValidationError('date_from must be before or equal to date_to.')
        if date_from and date_to and (date_to - date_from).days > MAX_DAYS_TO_SHOPPING_LIST:
            raise ValidationError(f'The shopping list cannot span more than {MAX_DAYS_TO_SHOPPING_LIST} days.')
        return super().validate(attrs)


class ShoppingLisItemtReadSerializer(ModelSerializer):
    ingredient = IngredientSerializer(read_only=True)

    class Meta:
        model = ShoppingListItem
        fields = [
            'id',
            'shopping_list',
            'ingredient',
            'amount',
            'owner',
            'is_checked',
            'checked_at',
            'is_manual',
            'position',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class ShoppingListItemWriteSerializer(ShoppingLisItemtReadSerializer):
    ingredient = UUIDField()
    is_manual = HiddenField(default=True)
    owner = HiddenField(default=CurrentUserDefault())
    shopping_list = HiddenField(default=CurrentShoppingList())

    class Meta(ShoppingLisItemtReadSerializer.Meta):
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]

    def to_representation(self, instance: ShoppingListItem) -> dict[str, Any]:
        return ShoppingLisItemtReadSerializer(instance, context=self.context).data

    def validate_ingredient(self, value: str) -> Ingredient:
        user = self.context['request'].user
        if isinstance(user, User):
            ingredient = Ingredient.objects.for_user(user).filter(pk=value).first()
        else:
            raise ValidationError('User is not authenticated.')
        if not ingredient:
            raise ValidationError('Ingredient with the given ID does not exist.')
        return ingredient

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        shopping_list: ShoppingList = attrs.get('shopping_list') or self.instance.shopping_list
        ingredient: Ingredient = attrs.get('ingredient') or self.instance.ingredient
        if self.instance:
            existing_items = shopping_list.items.exclude(pk=self.instance.pk)
        else:
            existing_items = shopping_list.items.all()
        if existing_items.filter(ingredient=ingredient).exists():
            raise ValidationError('This ingredient is already in the shopping list.')
        return super().validate(attrs)
