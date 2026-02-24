from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse
from rest_framework import status

STANDARD_ERROR_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: OpenApiResponse(
        description='Validation Error',
        response={
            'type': 'object',
            'properties': {
                'field_name': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Error messages for a specific field',
                },
                'non_field_errors': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Error messages not related to a specific field',
                },
            },
            'example': {
                'field': ['This field is required.'],
                'non_field_errors': [
                    'An error occurred not related to a specific field or you need send one of required fields.'
                ],
            },
        },
    ),
    status.HTTP_401_UNAUTHORIZED: OpenApiResponse(
        description='Error of authentication',
        response={
            'type': 'object',
            'properties': {'detail': {'type': 'string', 'description': 'Error message for authentication'}},
            'example': {'detail': 'Authentication credentials were not provided.'},
        },
    ),
    status.HTTP_403_FORBIDDEN: OpenApiResponse(
        description='Error of permission',
        response={
            'type': 'object',
            'properties': {'detail': {'type': 'string', 'description': 'Error message for permission'}},
            'example': {'detail': 'You do not have permission to perform this action.'},
        },
    ),
    status.HTTP_404_NOT_FOUND: OpenApiResponse(
        description='Resource not found',
        response={
            'type': 'object',
            'properties': {'detail': {'type': 'string', 'description': 'Error message for not found resource'}},
            'example': {'detail': 'Not found.'},
        },
    ),
    status.HTTP_429_TOO_MANY_REQUESTS: OpenApiResponse(
        description='Too many requests',
        response={
            'type': 'object',
            'properties': {'detail': {'type': 'string', 'description': 'Error message for too many requests'}},
            'example': {'detail': 'Request was throttled. Try again later.'},
        },
    ),
}


TG_INIT_DATA_HEADER = OpenApiParameter(
    'X-TG-INIT-DATA',
    type=OpenApiTypes.STR,
    description='Telegram Web App initialization data sent by Telegram in the header of the request',
    required=True,
)
