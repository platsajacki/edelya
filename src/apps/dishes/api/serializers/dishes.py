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


class DishReadSerializer(serializers.ModelSerializer):
    category = DishCategorySerializer(read_only=True)
    ingredients = IngredientSerializer(many=True, read_only=True)

    class Meta:
        model = Dish
        fields = [
            'id',
            'owner',
            'category',
            'ingredients',
            'name',
            'description',
            'is_active',
            'created_at',
            'updated_at',
        ]


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
        read_only_fields = [
            'id',
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


class DishSerializer(DishReadSerializer):
    ingredients = serializers.ListSerializer(
        child=DishIngredientSerializer(),
        write_only=True,
    )

    class Meta(DishReadSerializer.Meta): ...

    def to_representation(self, instance: Dish) -> dict:
        return DishReadSerializer(instance, context=self.context).data
