from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status

from apps.shopping.api.serializers.shopping_list import ShoppingLisItemtReadSerializer, ShoppingListSerializer
from core.schemas import STANDARD_ERROR_RESPONSES

SHOPPING_LIST_TAG = 'Shopping Lists'


class ShoppingListViewSetSchema:
    list = extend_schema(
        tags=[SHOPPING_LIST_TAG],
        summary='List shopping lists',
        description='Retrieve a list of shopping lists for the authenticated user.',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='A list of shopping lists', response=ShoppingListSerializer(many=True)
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    retrieve = extend_schema(
        tags=[SHOPPING_LIST_TAG],
        summary='Retrieve a shopping list',
        description='Retrieve details of a specific shopping list by its ID.',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Details of the shopping list', response=ShoppingListSerializer()
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    create = extend_schema(
        tags=[SHOPPING_LIST_TAG],
        summary='Create a shopping list',
        description='Create a shopping list for the authenticated user. Items are recalculated automatically.',
        request=ShoppingListSerializer(),
        responses={
            status.HTTP_201_CREATED: OpenApiResponse(
                description='The created shopping list', response=ShoppingListSerializer()
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    partial_update = extend_schema(
        tags=[SHOPPING_LIST_TAG],
        summary='Partially update a shopping list',
        description='Partially update shopping list attributes (name, date range). Items will be recalculated.',
        request=ShoppingListSerializer(partial=True),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='The updated shopping list', response=ShoppingListSerializer()
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    destroy = extend_schema(
        tags=[SHOPPING_LIST_TAG],
        summary='Delete a shopping list',
        description='Delete a shopping list and its items.',
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description='Shopping list deleted successfully'),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    recalculate = extend_schema(
        tags=[SHOPPING_LIST_TAG],
        summary='Recalculate shopping list items',
        description=(
            'Triggers a full recalculation of non-manual shopping list items based on '
            "cooking events that fall within the list's date range. "
            'Manual items are preserved.'
        ),
        request=None,
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Shopping list recalculated successfully',
                response={
                    'type': 'object',
                    'properties': {'detail': {'type': 'string'}},
                    'example': {'detail': 'Shopping list recalculated successfully.'},
                },
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )


SHOPPING_LIST_ITEM_TAG = 'Shopping List Items'


class ShoppingListItemViewSetSchema:
    list = extend_schema(
        tags=[SHOPPING_LIST_ITEM_TAG],
        summary='List shopping list items',
        description='Retrieve all items for the given shopping list.',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='A list of shopping list items', response=ShoppingLisItemtReadSerializer(many=True)
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    retrieve = extend_schema(
        tags=[SHOPPING_LIST_ITEM_TAG],
        summary='Retrieve a shopping list item',
        description='Retrieve details of a specific shopping list item.',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Details of the shopping list item', response=ShoppingLisItemtReadSerializer()
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    create = extend_schema(
        tags=[SHOPPING_LIST_ITEM_TAG],
        summary='Create a shopping list item',
        description='Manually add an ingredient item to the shopping list. The item is always marked as manual.',
        responses={
            status.HTTP_201_CREATED: OpenApiResponse(
                description='The created shopping list item', response=ShoppingLisItemtReadSerializer()
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    partial_update = extend_schema(
        tags=[SHOPPING_LIST_ITEM_TAG],
        summary='Partially update a shopping list item',
        description='Update fields of a manual shopping list item.',
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='The updated shopping list item', response=ShoppingLisItemtReadSerializer()
            ),
            **STANDARD_ERROR_RESPONSES,
        },
    )
    destroy = extend_schema(
        tags=[SHOPPING_LIST_ITEM_TAG],
        summary='Delete a shopping list item',
        description='Delete a shopping list item.',
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description='Item deleted successfully'),
            **STANDARD_ERROR_RESPONSES,
        },
    )
