from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status

from apps.planning.api.serializers.cooking import CookingEventSerializer, CookingEventWriteSerializer
from apps.planning.api.serializers.meal_plan import (
    MealPlanItemCreateSerializer,
    MealPlanItemSerializer,
    MealPlanItemUpdateSerializer,
    WeekDishesSerializer,
)
from core.schemas import STANDARD_ERROR_RESPONSES

WEEK_TAG = 'Planning'
COOKING_EVENT_TAG = 'Cooking Events'
MEAL_PLAN_TAG = 'Meal Plan'


class WeekDishesAPIViewSchema:
    get = extend_schema(
        tags=[WEEK_TAG],
        summary='Get week dishes',
        description='Retrieve all dishes planned for a specific week of a given year.',
        parameters=[
            OpenApiParameter(
                name='year', location=OpenApiParameter.PATH, description='Year number', required=True, type=int
            ),
            OpenApiParameter(
                name='week', location=OpenApiParameter.PATH, description='Week number', required=True, type=int
            ),
        ],
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='A list of dishes for the week',
                response=WeekDishesSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )


class CookingEventViewSetSchema:
    list = extend_schema(
        tags=[COOKING_EVENT_TAG],
        summary='List cooking events',
        description='Retrieve a list of all cooking events for the authenticated user.',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='A list of cooking events',
                response=CookingEventSerializer(many=True),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    retrieve = extend_schema(
        tags=[COOKING_EVENT_TAG],
        summary='Retrieve a cooking event',
        description='Retrieve details of a specific cooking event by its ID.',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Details of the cooking event',
                response=CookingEventSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    create = extend_schema(
        tags=[COOKING_EVENT_TAG],
        summary='Create a cooking event',
        description=(
            'Creates a new cooking event for the authenticated user. '
            'Accepts `eat_dates` — a list of dates (YYYY-MM-DD) representing days when the dish will be eaten. '
            'All `eat_dates` must be on or after `cooking_date`. '
            'Non-manual meal plan items will be created for each date in `eat_dates`.'
        ),
        request=CookingEventWriteSerializer(),
        responses={
            status.HTTP_201_CREATED: OpenApiResponse(
                description='The created cooking event',
                response=CookingEventSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    partial_update = extend_schema(
        tags=[COOKING_EVENT_TAG],
        summary='Partially update a cooking event',
        description=(
            'Partially update an existing cooking event. '
            'Provide `eat_dates` (a list of dates) to synchronize meal plan items: '
            'dates removed from `eat_dates` will be deleted, and new dates will get new non-manual meal plan items. '
            'All `eat_dates` must be on or after `cooking_date`.'
        ),
        request=CookingEventWriteSerializer(partial=True),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='The updated cooking event',
                response=CookingEventSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    destroy = extend_schema(
        tags=[COOKING_EVENT_TAG],
        summary='Delete a cooking event',
        description='Delete a cooking event and all its associated meal plan items.',
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description='Cooking event deleted successfully'),
            **STANDARD_ERROR_RESPONSES,
        },
    )


class MealPlanItemViewSetSchema:
    create = extend_schema(
        tags=[MEAL_PLAN_TAG],
        summary='Create meal plan items',
        description=(
            'Creates manual meal plan items for the authenticated user. '
            'Accepts `eat_dates` — a list of dates (YYYY-MM-DD) representing days when the dish will be eaten. '
            'A separate meal plan item is created for each date. '
            'Position auto-increments by 100 for each subsequent item starting '
            'from the provided position (default 100).'
        ),
        request=MealPlanItemCreateSerializer(),
        responses={
            status.HTTP_201_CREATED: OpenApiResponse(
                description='The created meal plan items',
                response=MealPlanItemSerializer(many=True),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    partial_update = extend_schema(
        tags=[MEAL_PLAN_TAG],
        summary='Partially update a meal plan item',
        description='Partially update an existing meal plan item (e.g. change its date or position).',
        request=MealPlanItemUpdateSerializer(partial=True),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='The updated meal plan item',
                response=MealPlanItemUpdateSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    destroy = extend_schema(
        tags=[MEAL_PLAN_TAG],
        summary='Delete a meal plan item',
        description='Delete a manual meal plan item belonging to the authenticated user.',
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description='Meal plan item deleted successfully'),
            **STANDARD_ERROR_RESPONSES,
        },
    )
