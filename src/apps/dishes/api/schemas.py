from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status

from apps.dishes.api.serializers.dishes import DishCategorySerializer
from apps.dishes.api.serializers.ingredients import IngredientCategorySerializer, IngredientSerializer
from core.schemas import STANDARD_ERROR_RESPONSES

INGREDIENT_CATEGORY_TAG = 'Ingredient Categories'
INGREDIENT_TAG = 'Ingredients'
DISH_CATEGORY_TAG = 'Dish Categories'


class IngredientCategoryViewSetSchema:
    list = extend_schema(
        tags=[INGREDIENT_CATEGORY_TAG],
        summary='List all ingredient categories',
        description='Retrieve a list of all active ingredient categories.',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='A list of ingredient categories',
                response=IngredientCategorySerializer(many=True),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    retrieve = extend_schema(
        tags=[INGREDIENT_CATEGORY_TAG],
        summary='Retrieve an ingredient category',
        description='Retrieve details of a specific ingredient category by its ID.',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Details of the ingredient category',
                response=IngredientCategorySerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )


class DishCategoryViewSetSchema:
    list = extend_schema(
        tags=[DISH_CATEGORY_TAG],
        summary='List all dish categories',
        description='Retrieve a list of all active dish categories.',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='A list of dish categories',
                response=DishCategorySerializer(many=True),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    retrieve = extend_schema(
        tags=[DISH_CATEGORY_TAG],
        summary='Retrieve a dish category',
        description='Retrieve details of a specific dish category by its ID.',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Details of the dish category',
                response=DishCategorySerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )


class IngredientViewSetSchema:
    list = extend_schema(
        tags=[INGREDIENT_TAG],
        summary='List all ingredients',
        description='Retrieve a list of all ingredients for the authenticated user.',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='A list of ingredients',
                response=IngredientSerializer(many=True),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    retrieve = extend_schema(
        tags=[INGREDIENT_TAG],
        summary='Retrieve an ingredient',
        description='Retrieve details of a specific ingredient by its ID.',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Details of the ingredient',
                response=IngredientSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    create = extend_schema(
        tags=[INGREDIENT_TAG],
        summary='Create a new ingredient',
        description='Create a new ingredient for the authenticated user.',
        request=IngredientSerializer(),
        responses={
            status.HTTP_201_CREATED: OpenApiResponse(
                description='The created ingredient',
                response=IngredientSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    update = extend_schema(
        tags=[INGREDIENT_TAG],
        summary='Update an ingredient',
        description='Update an existing ingredient by its ID.',
        request=IngredientSerializer(),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='The updated ingredient',
                response=IngredientSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    partial_update = extend_schema(
        tags=[INGREDIENT_TAG],
        summary='Partially update an ingredient',
        description='Partially update an existing ingredient by its ID.',
        request=IngredientSerializer(partial=True),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='The updated ingredient',
                response=IngredientSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    destroy = extend_schema(
        tags=[INGREDIENT_TAG],
        summary='Delete an ingredient',
        description='Delete an existing ingredient by its ID.',
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description='Ingredient deleted successfully'),
            **STANDARD_ERROR_RESPONSES,
        },
    )
