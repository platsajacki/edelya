from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status

from apps.users.api.serializers.legal_docs import PrivacyPolicyVersionSerializer, TermsOfServiceVersionSerializer
from apps.users.api.serializers.users import OnboardingDataSerializer
from core.schemas import STANDARD_ERROR_RESPONSES

TAG = 'Users'
TAG_LEGAL = 'Legal'


class TermsOfServiceVersionViewSetSchema:
    custom_actions = {'latest'}

    list = extend_schema(
        tags=[TAG_LEGAL],
        summary='List all Terms of Service versions',
        description=(
            'Returns all Terms of Service versions ordered from newest to oldest. '
            'Use this endpoint to display a version history. '
            'To get only the current active version, use `GET /legal/terms-of-service/latest/`.'
        ),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='List of Terms of Service versions, newest first.',
                response=TermsOfServiceVersionSerializer(many=True),
            ),
        },
    )
    latest = extend_schema(
        tags=[TAG_LEGAL],
        summary='Get current Terms of Service version',
        description=(
            'Returns the latest active Terms of Service version. '
            'This is the version that should be shown to the user before consent. '
            'Returns `404` if no active version exists.'
        ),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='The current active Terms of Service version.',
                response=TermsOfServiceVersionSerializer(),
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(
                description='No active Terms of Service version found.',
            ),
        },
    )


class PrivacyPolicyVersionViewSetSchema:
    custom_actions = {'latest'}

    list = extend_schema(
        tags=[TAG_LEGAL],
        summary='List all Privacy Policy versions',
        description=(
            'Returns all Privacy Policy versions ordered from newest to oldest. '
            'Use this endpoint to display a version history. '
            'To get only the current active version, use `GET /legal/privacy-policy/latest/`.'
        ),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='List of Privacy Policy versions, newest first.',
                response=PrivacyPolicyVersionSerializer(many=True),
            ),
        },
    )
    latest = extend_schema(
        tags=[TAG_LEGAL],
        summary='Get current Privacy Policy version',
        description=(
            'Returns the latest active Privacy Policy version. '
            'This is the version that should be shown to the user before consent. '
            'Returns `404` if no active version exists.'
        ),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='The current active Privacy Policy version.',
                response=PrivacyPolicyVersionSerializer(),
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(
                description='No active Privacy Policy version found.',
            ),
        },
    )


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
