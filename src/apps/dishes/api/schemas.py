from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status

from apps.dishes.api.serializers.ai_drafts import DishAIDraftSerializer
from apps.dishes.api.serializers.dishes import DishCategorySerializer, DishReadSerializer, DishWriteSerializer
from apps.dishes.api.serializers.ingredients import IngredientCategorySerializer, IngredientSerializer
from core.schemas import STANDARD_ERROR_RESPONSES

AI_DRAFT_TAG = 'AI Drafts'
INGREDIENT_CATEGORY_TAG = 'Ingredient Categories'
INGREDIENT_TAG = 'Ingredients'
DISH_CATEGORY_TAG = 'Dish Categories'
DISH_TAG = 'Dishes'


class DishAIDraftViewSetSchema:
    list = extend_schema(
        tags=[AI_DRAFT_TAG],
        summary='List AI dish drafts',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='A paginated list of AI dish drafts',
                response=DishAIDraftSerializer(many=True),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    create = extend_schema(
        tags=[AI_DRAFT_TAG],
        summary='Create AI dish draft',
        request=DishAIDraftSerializer(),
        responses={
            status.HTTP_201_CREATED: OpenApiResponse(
                description='The created AI dish draft',
                response=DishAIDraftSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
            status.HTTP_403_FORBIDDEN: OpenApiResponse(
                description=(
                    'AI recipe creation is forbidden. Possible reasons: '
                    'the current tariff does not include AI recipe creation; '
                    'the AI recipe limit for the current subscription period has been exceeded.'
                ),
                response={
                    'type': 'object',
                    'properties': {
                        'detail': {'type': 'string', 'description': 'Error message'},
                        'code': {'type': 'string', 'description': 'Machine-readable error code'},
                        'reset_at': {
                            'type': 'string',
                            'format': 'date-time',
                            'nullable': True,
                            'description': 'Subscription period limit reset time',
                        },
                    },
                    'required': ['detail'],
                    'example': {
                        'detail': 'AI recipe limit for the current subscription period has been exceeded.',
                        'code': 'ai_recipe_limit_exceeded',
                        'reset_at': '2026-06-30T12:00:00+00:00',
                    },
                },
            ),
        },
    )
    retrieve = extend_schema(
        tags=[AI_DRAFT_TAG],
        summary='Retrieve AI dish draft',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Details of the AI dish draft',
                response=DishAIDraftSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )


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


class DishViewSetSchema:
    list = extend_schema(
        tags=[DISH_TAG],
        summary='List dishes',
        description=(
            'Returns a paginated list of dishes available to the authenticated user. '
            'Includes global dishes (no owner) and dishes created by the user. '
        ),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='A paginated list of dishes',
                response=DishReadSerializer(many=True),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    retrieve = extend_schema(
        tags=[DISH_TAG],
        summary='Retrieve a dish',
        description=(
            'Returns full details of a specific dish by its ID, '
            'including all ingredients. '
            'The owner can access their own dishes; global dishes (no owner) are readable by any authenticated user '
            'but cannot be modified or deleted.'
        ),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Details of the dish',
                response=DishReadSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    create = extend_schema(
        tags=[DISH_TAG],
        summary='Create a dish',
        description=(
            'Creates a new dish for the authenticated user. '
            'At least one ingredient must be provided. '
            'Dish names must be unique per user. '
            'Only ingredients owned by the user or global ingredients can be used.'
        ),
        request=DishWriteSerializer(),
        responses={
            status.HTTP_201_CREATED: OpenApiResponse(
                description='The created dish',
                response=DishReadSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    update = extend_schema(
        tags=[DISH_TAG],
        summary='Update a dish',
        description=(
            'Fully replaces an existing dish. '
            'The supplied ingredient list completely replaces the previous one: '
            'ingredients not present in the request will be removed, new ones will be added, '
            'and existing ones will be updated in place. '
            'Only the owner can update their dish; global dishes cannot be modified.'
        ),
        request=DishWriteSerializer(),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='The updated dish',
                response=DishReadSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    destroy = extend_schema(
        tags=[DISH_TAG],
        summary='Delete a dish',
        description=(
            'Deactivates the dish and removes all its ingredient associations. '
            'Only the owner can delete their dish; global dishes cannot be deleted.'
        ),
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description='Dish deleted successfully'),
            **STANDARD_ERROR_RESPONSES,
        },
    )
