from drf_spectacular.utils import OpenApiRequest, OpenApiResponse, extend_schema
from rest_framework import status

from core.schemas import TG_INIT_DATA_HEADER

TAG = 'Authentication'


class TelegramA12nJWTSchema:
    post = extend_schema(
        tags=[TAG],
        summary='Obtain JWT token pair using Telegram Web App initialization data',
        description=(
            'This endpoint allows clients to obtain a JWT token pair (access and refresh tokens) by '
            'providing Telegram Web App initialization data. The initialization data is sent by '
            'Telegram in the header of the request.'
        ),
        request=OpenApiRequest(),
        parameters=[TG_INIT_DATA_HEADER],
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Successful authentication',
                response={
                    'type': 'object',
                    'properties': {
                        'refresh': {'type': 'string', 'description': 'JWT refresh token'},
                        'access': {'type': 'string', 'description': 'JWT access token'},
                    },
                },
            ),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(
                description='Invalid Telegram data',
                response={
                    'type': 'object',
                    'properties': {
                        'detail': {'type': 'string', 'description': 'Error message for invalid Telegram data'}
                    },
                    'example': {'detail': 'Invalid Telegram data'},
                },
            ),
        },
    )


class LoginTokenObtainPairViewSchema:
    post = extend_schema(
        tags=[TAG],
        summary='Obtain JWT token pair using username and password',
        description=(
            'This endpoint accepts a username and password and returns a JWT token pair (access and refresh tokens).'
        ),
        request=OpenApiRequest(
            request={
                'type': 'object',
                'properties': {
                    'username': {'type': 'string', 'description': 'Account username'},
                    'password': {'type': 'string', 'description': 'Account password'},
                },
                'required': ['username', 'password'],
            },
        ),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Successful authentication',
                response={
                    'type': 'object',
                    'properties': {
                        'refresh': {'type': 'string', 'description': 'JWT refresh token'},
                        'access': {'type': 'string', 'description': 'JWT access token'},
                    },
                },
            ),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(
                description='Invalid credentials',
                response={
                    'type': 'object',
                    'properties': {
                        'detail': {'type': 'string', 'description': 'Error message for invalid credentials'}
                    },
                    'example': {'detail': 'No active account found with the given credentials'},
                },
            ),
        },
    )


class TokenRefreshViewSchema:
    post = extend_schema(
        tags=[TAG],
        summary='Refresh JWT access token using refresh token',
        description=(
            'This endpoint accepts a JWT refresh token and returns a new access token. '
            'Clients should provide the `refresh` token in the request body.'
        ),
        request=OpenApiRequest(
            request={
                'type': 'object',
                'properties': {
                    'refresh': {'type': 'string', 'description': 'JWT refresh token'},
                },
                'required': ['refresh'],
            },
        ),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='New access token',
                response={
                    'type': 'object',
                    'properties': {
                        'access': {'type': 'string', 'description': 'JWT access token'},
                        'refresh': {'type': 'string', 'description': 'JWT refresh token'},
                    },
                },
            ),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(
                description='Invalid or expired refresh token',
                response={
                    'type': 'object',
                    'properties': {'detail': {'type': 'string', 'description': 'Error message for invalid token'}},
                    'example': {'detail': 'Token is invalid or expired'},
                },
            ),
        },
    )
