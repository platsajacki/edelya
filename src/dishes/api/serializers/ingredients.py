from rest_framework import serializers

from app.base.validators import UniqueTogetherWithOperatorValidator
from dishes.models import Ingredient, IngredientCategory


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


class IngredientSerializer(serializers.ModelSerializer):
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
        data = super().to_representation(instance)
        data['category'] = IngredientCategorySerializer(instance.category).data
        return data
