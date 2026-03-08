from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status

from apps.planning.api.serializers.meal_plan import WeekDishesSerializer
from core.schemas import STANDARD_ERROR_RESPONSES

WEEK_TAG = 'Planning'


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
