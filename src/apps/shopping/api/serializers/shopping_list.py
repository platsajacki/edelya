from typing import Any

from rest_framework.exceptions import ValidationError
from rest_framework.fields import HiddenField
from rest_framework.serializers import CurrentUserDefault, ModelSerializer, UUIDField

from apps.dishes.api.serializers.ingredients import IngredientSerializer
from apps.dishes.models import Ingredient
from apps.shopping.models import ShoppingList, ShoppingListItem
from apps.users.models import User
from core.base.serialisers import CurrentShoppingList


class ShoppingListSerializer(ModelSerializer):
    owner = HiddenField(default=CurrentUserDefault())

    class Meta:
        model = ShoppingList
        fields = ['id', 'name', 'date_from', 'date_to', 'owner']


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
