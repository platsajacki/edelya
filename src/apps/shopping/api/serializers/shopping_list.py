from rest_framework.serializers import ModelSerializer

from apps.dishes.api.serializers.ingredients import IngredientSerializer
from apps.shopping.models import ShoppingList, ShoppingListItem


class ShoppingListSerializer(ModelSerializer):
    class Meta:
        model = ShoppingList
        fields = ['id', 'name', 'date_from', 'date_to']


class ShoppingListItemSerializer(ModelSerializer):
    class Meta:
        model = ShoppingListItem
        fields = ['id', 'ingredient', 'amount', 'is_checked', 'checked_at']

    def to_representation(self, instance: ShoppingListItem) -> dict:
        data = super().to_representation(instance)
        data['ingredient'] = IngredientSerializer(instance.ingredient).data
        return data
