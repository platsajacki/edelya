from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status

from apps.subscriptions.api.serializers.subscriptions import SubscriptionSerializer
from apps.subscriptions.api.serializers.tariffs import TariffSerializer
from core.schemas import STANDARD_ERROR_RESPONSES

SUBSCRIPTION_TAG = 'Subscriptions'
TARIFF_TAG = 'Tariffs'


class TariffViewSetSchema:
    custom_actions = {'trial_duration'}

    list = extend_schema(
        tags=[TARIFF_TAG],
        summary='List tariffs',
        description='Retrieve a list of published and active tariffs.',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='A list of tariffs',
                response=TariffSerializer(many=True),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    retrieve = extend_schema(
        tags=[TARIFF_TAG],
        summary='Retrieve a tariff',
        description='Retrieve details of a specific tariff.',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Tariff details',
                response=TariffSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    trial_duration = extend_schema(
        tags=[TARIFF_TAG],
        summary='Get trial duration',
        description='Retrieve the duration of the trial period in days.',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Trial duration in days',
                response={
                    'type': 'object',
                    'properties': {
                        'trial_duration': {'type': 'integer'},
                    },
                    'required': ['trial_duration'],
                },
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )


class SubscriptionViewSetSchema:
    custom_actions = {'me', 'start_trial'}

    me = extend_schema(
        tags=[SUBSCRIPTION_TAG],
        summary='Get current subscription',
        description='Retrieve the current subscription of the authenticated user.',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Current subscription',
                response=SubscriptionSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    start_trial = extend_schema(
        tags=[SUBSCRIPTION_TAG],
        summary='Start trial',
        description=(
            'Start a free trial for the authenticated user. '
            'Only possible if no subscription exists yet. '
            'The trial tariff is assigned automatically.'
        ),
        request=None,
        responses={
            status.HTTP_201_CREATED: OpenApiResponse(
                description='Trial subscription created',
                response=SubscriptionSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
