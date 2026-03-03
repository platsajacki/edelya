from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from apps.dishes.api.serializers.ingredients import IngredientSerializer
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


class DishSerializer(serializers.ModelSerializer):
    ingredients = IngredientSerializer(
        source='dish_ingredients',
        many=True,
        read_only=True,
    )

    class Meta:
        model = Dish
        fields = [
            'id',
            'owner',
            'category',
            'name',
            'description',
            'is_active',
            'created_at',
            'updated_at',
        ]

    def to_representation(self, instance: Dish) -> dict:
        data = super().to_representation(instance)
        data['category'] = DishCategorySerializer(instance.category).data
        return data


class DishIngredientSerializer(serializers.ModelSerializer):
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
        validators = [
            UniqueTogetherValidator(
                queryset=DishIngredient.objects.all(),
                fields=['dish', 'ingredient'],
                message='Such ingredient already exists in this dish.',
            ),
        ]
