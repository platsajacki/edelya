from rest_framework import serializers

from apps.dishes.models import Ingredient, IngredientCategory
from core.base.validators import UniqueTogetherWithOperatorValidator


class IngredientCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = IngredientCategory
        fields = [
            'id',
            'name',
            'is_active',
            'created_at',
            'updated_at',
        ]


class IngredientReadSerializer(serializers.ModelSerializer):
    category = IngredientCategorySerializer(read_only=True)

    class Meta:
        model = Ingredient
        fields = [
            'id',
            'name',
            'owner',
            'base_unit',
            'is_active',
            'category',
            'created_at',
            'updated_at',
        ]


class IngredientWriteSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Ingredient
        fields = [
            'id',
            'name',
            'owner',
            'base_unit',
            'is_active',
            'category',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'is_active',
            'created_at',
            'updated_at',
        ]
        validators = [
            UniqueTogetherWithOperatorValidator(
                queryset=Ingredient.objects.actived(),
                fields=['name__iexact', 'owner'],
                message='An ingredient with this name already exists for this user.',
            )
        ]

    def to_representation(self, instance: Ingredient) -> dict:
        return IngredientReadSerializer(instance).data
