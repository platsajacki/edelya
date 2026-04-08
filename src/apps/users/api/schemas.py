from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status

from apps.users.api.serializers.users import OnboardingDataSerializer
from core.schemas import STANDARD_ERROR_RESPONSES

TAG = 'Users'


class OnboardingDataViewSchema:
    get = extend_schema(
        tags=[TAG],
        summary='Retrieve onboarding data',
        description=(
            'Retrieve onboarding data for the currently authenticated user. '
            'The `onboarding_data` field is a key→boolean map: keys name steps, '
            'values are flags (true/false) indicating completion. Keys cannot be removed — '
            'they may only be added or updated.'
        ),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Onboarding data of the authenticated user. '
                'See `onboarding_data` description above for semantics.',
                response=OnboardingDataSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    patch = extend_schema(
        tags=[TAG],
        summary='Update onboarding data',
        description=(
            'Partially update onboarding data for the currently authenticated user. '
            'Provide a map of step keys to boolean values (true/false). '
            'Existing keys must not be removed; you may add new keys or change values.'
        ),
        request=OnboardingDataSerializer(partial=True),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Updated onboarding data. See request description for field semantics.',
                response=OnboardingDataSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
