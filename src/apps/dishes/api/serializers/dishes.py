from rest_framework import serializers

from apps.dishes.api.serializers.ingredients import IngredientSerializer
from apps.dishes.contstants import MAX_INGREDIENTS_PER_DISH
from apps.dishes.models import Dish, DishCategory, DishIngredient


class DishCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DishCategory
        fields = [
            'id',
            'name',
            'is_active',
            'created_at',
            'updated_at',
        ]


class DishIngredientSerializer(serializers.ModelSerializer):
    ingredient = IngredientSerializer(read_only=True)

    class Meta:
        model = DishIngredient
        fields = [
            'id',
            'dish',
            'ingredient',
            'is_optional',
            'amount',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]


class DishReadSerializer(serializers.ModelSerializer):
    category = DishCategorySerializer(read_only=True)
    dish_ingredients = DishIngredientSerializer(many=True, read_only=True)

    class Meta:
        model = Dish
        fields = [
            'id',
            'owner',
            'category',
            'dish_ingredients',
            'name',
            'description',
            'is_active',
            'created_at',
            'updated_at',
        ]


class DishIngredientWriteSerializer(serializers.Serializer):
    ingredient = serializers.UUIDField(
        label='Ingredient ID',
        help_text='The ID of the ingredient to add to the dish.',
    )
    is_optional = serializers.BooleanField(
        default=False,
        help_text='Whether the ingredient is optional in the dish.',
    )
    amount = serializers.DecimalField(
        label='Amount',
        max_digits=12,
        decimal_places=3,
        min_value=0,
        help_text="The amount of the ingredient needed for the dish, in the ingredient's base unit.",
    )


class DishWriteSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    dish_ingredients = DishIngredientWriteSerializer(
        many=True,
        required=False,
        default=list,
        help_text=f'List of ingredients for the dish. Max {MAX_INGREDIENTS_PER_DISH} ingredients allowed.',
    )

    class Meta:
        model = Dish
        fields = [
            'owner',
            'category',
            'name',
            'description',
            'dish_ingredients',
        ]

    def validate_dish_ingredients(self, value: list[dict]) -> list[dict]:
        if not value:
            raise serializers.ValidationError('At least one ingredient is required.')
        ingredient_ids = [item['ingredient'] for item in value]
        length = len(ingredient_ids)
        if length != len(set(ingredient_ids)):
            raise serializers.ValidationError('Duplicate ingredients are not allowed.')
        if length > MAX_INGREDIENTS_PER_DISH:
            raise serializers.ValidationError(f'Maximum {MAX_INGREDIENTS_PER_DISH} ingredients are allowed.')
        return value
