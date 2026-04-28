from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status

from apps.subscriptions.api.serializers.payment_methods import PaymentMethodSerializer
from apps.subscriptions.api.serializers.subscriptions import SubscriptionSerializer
from apps.subscriptions.api.serializers.tariffs import TariffSerializer
from core.schemas import STANDARD_ERROR_RESPONSES

PAYMENT_METHOD_TAG = 'Payment Methods'
SUBSCRIPTION_TAG = 'Subscriptions'
TARIFF_TAG = 'Tariffs'


class PaymentMethodViewSetSchema:
    get = extend_schema(
        tags=[PAYMENT_METHOD_TAG],
        summary='Bind a payment method',
        description=(
            'Initiates a YooKassa card binding flow. '
            'Returns a `confirmation_url` to redirect the user to for card entry. '
            'Returns **409** if a payment method already exists — delete it first.'
        ),
        request=None,
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Card binding initiated — open `confirmation_url` in a browser or WebView',
                response={
                    'type': 'object',
                    'properties': {
                        'action': {'type': 'string', 'enum': ['redirect']},
                        'confirmation_url': {'type': 'string', 'format': 'uri'},
                        'context': {'type': 'string', 'enum': ['card_binding']},
                        'description': {'type': 'string'},
                    },
                    'required': ['action', 'confirmation_url', 'context', 'description'],
                },
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    post = extend_schema(
        tags=[PAYMENT_METHOD_TAG],
        summary='Retrieve payment method',
        description='Returns the saved payment method of the authenticated user. Returns **404** if no card is bound.',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Saved payment method',
                response=PaymentMethodSerializer(),
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    delete = extend_schema(
        tags=[PAYMENT_METHOD_TAG],
        summary='Delete payment method',
        description=(
            'Deletes the saved payment method of the authenticated user. '
            'Deleting a card while an active paid subscription is running will prevent automatic renewal.'
        ),
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description='Payment method deleted'),
            **STANDARD_ERROR_RESPONSES,
        },
    )


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
    custom_actions = {'me', 'start_trial', 'select_tariff'}

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
    select_tariff = extend_schema(
        tags=[SUBSCRIPTION_TAG],
        summary='Select a tariff',
        description=(
            'Switch the current subscription to a different tariff.\n\n'
            '**Possible outcomes depending on the current subscription state:**\n\n'
            '- **No card on file** — the user is redirected to a card binding page. '
            'After the card is saved, the selected tariff will be applied automatically.\n\n'
            '- **Inactive subscription (expired or cancelled)** — the user is redirected to a payment page '
            'to pay for the selected tariff and re-activate the subscription.\n\n'
            '- **Active subscription, downgrade (cheaper tariff)** — the new tariff is scheduled '
            'and will take effect at the start of the next billing cycle. No charge is made now.\n\n'
            '- **Active subscription, upgrade (more expensive tariff)** — the user is charged a prorated '
            'amount for the remaining days of the current period, and the new tariff is activated immediately.\n\n'
            '**Response format:**\n\n'
            'The `action` field indicates what the client should do:\n'
            '- `redirect` — open the `confirmation_url` in a browser. '
            'The `context` field clarifies the reason: `card_binding` or `payment`.\n'
            '- `success` — no further action needed. '
            'The updated subscription is included in the `subscription` field.\n\n'
            'The `description` field always contains a human-readable explanation of what '
            'happened or what is expected from the user.'
        ),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Tariff selection result',
                response={
                    'oneOf': [
                        {
                            'type': 'object',
                            'title': 'Redirect',
                            'properties': {
                                'action': {'type': 'string', 'enum': ['redirect']},
                                'confirmation_url': {'type': 'string', 'format': 'uri'},
                                'context': {'type': 'string', 'enum': ['card_binding', 'payment']},
                                'description': {'type': 'string'},
                            },
                            'required': ['action', 'confirmation_url', 'context', 'description'],
                        },
                        {
                            'type': 'object',
                            'title': 'Success',
                            'properties': {
                                'action': {'type': 'string', 'enum': ['success']},
                                'subscription': {'type': 'object'},
                                'description': {'type': 'string'},
                            },
                            'required': ['action', 'subscription', 'description'],
                        },
                    ]
                },
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
