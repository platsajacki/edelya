import pytest

import uuid
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.dishes.models import Ingredient
from apps.shopping.models import ShoppingList, ShoppingListItem
from apps.users.models import User


def item_list_url(shopping_list_id: str) -> str:
    return reverse(
        'api_v1:shopping:shopping:shopping-list-item-list',
        kwargs={'shopping_list_id': shopping_list_id},
    )


def item_detail_url(shopping_list_id: str, item_id: str) -> str:
    return reverse(
        'api_v1:shopping:shopping:shopping-list-item-detail',
        kwargs={'shopping_list_id': shopping_list_id, 'shopping_list_item_id': item_id},
    )


@pytest.fixture
def item_payload(ingredient_global: Ingredient) -> dict:
    return {
        'ingredient': str(ingredient_global.id),
        'manual_amount': '150.000',
    }


class TestShoppingListItemViewSetList:
    def test_anon_client_cannot_list(self, api_client: APIClient, shopping_list: ShoppingList) -> None:
        response = api_client.get(item_list_url(str(shopping_list.id)))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_client_gets_empty_list(
        self, auth_telegram_api_client: APIClient, shopping_list: ShoppingList
    ) -> None:
        response = auth_telegram_api_client.get(item_list_url(str(shopping_list.id)))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0

    def test_owner_sees_own_items(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        shopping_list_item: ShoppingListItem,
        manual_shopping_list_item: ShoppingListItem,
    ) -> None:
        response = auth_telegram_api_client.get(item_list_url(str(shopping_list.id)))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2

    def test_another_user_cannot_see_items(
        self,
        auth_another_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        shopping_list_item: ShoppingListItem,
    ) -> None:
        response = auth_another_telegram_api_client.get(item_list_url(str(shopping_list.id)))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0

    def test_nonexistent_shopping_list_returns_empty(self, auth_telegram_api_client: APIClient) -> None:
        response = auth_telegram_api_client.get(item_list_url(str(uuid.uuid4())))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0


class TestShoppingListItemViewSetRetrieve:
    def test_anon_client_cannot_retrieve(
        self,
        api_client: APIClient,
        shopping_list: ShoppingList,
        shopping_list_item: ShoppingListItem,
    ) -> None:
        response = api_client.get(item_detail_url(str(shopping_list.id), str(shopping_list_item.id)))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_owner_can_retrieve_item(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        shopping_list_item: ShoppingListItem,
    ) -> None:
        response = auth_telegram_api_client.get(item_detail_url(str(shopping_list.id), str(shopping_list_item.id)))
        assert response.status_code == status.HTTP_200_OK
        assert str(response.data['id']) == str(shopping_list_item.id)

    def test_another_user_cannot_retrieve_item(
        self,
        auth_another_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        shopping_list_item: ShoppingListItem,
    ) -> None:
        response = auth_another_telegram_api_client.get(
            item_detail_url(str(shopping_list.id), str(shopping_list_item.id))
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nonexistent_item_returns_404(
        self, auth_telegram_api_client: APIClient, shopping_list: ShoppingList
    ) -> None:
        response = auth_telegram_api_client.get(item_detail_url(str(shopping_list.id), str(uuid.uuid4())))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_response_contains_expected_fields(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        shopping_list_item: ShoppingListItem,
    ) -> None:
        response = auth_telegram_api_client.get(item_detail_url(str(shopping_list.id), str(shopping_list_item.id)))
        assert response.status_code == status.HTTP_200_OK
        assert set(response.data.keys()) >= {
            'id',
            'shopping_list',
            'ingredient',
            'amount',
            'is_checked',
            'is_manual',
            'position',
        }


class TestShoppingListItemViewSetCreate:
    def test_anon_client_cannot_create(
        self, api_client: APIClient, shopping_list: ShoppingList, item_payload: dict
    ) -> None:
        response = api_client.post(item_list_url(str(shopping_list.id)), data=item_payload, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_valid_payload_creates_item(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        item_payload: dict,
    ) -> None:
        response = auth_telegram_api_client.post(item_list_url(str(shopping_list.id)), data=item_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert ShoppingListItem.objects.filter(shopping_list=shopping_list).count() == 1

    def test_created_item_is_always_manual(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        item_payload: dict,
    ) -> None:
        auth_telegram_api_client.post(item_list_url(str(shopping_list.id)), data=item_payload, format='json')
        item = ShoppingListItem.objects.get(shopping_list=shopping_list)
        assert item.is_manual is True

    def test_passing_is_manual_false_is_ignored(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        item_payload: dict,
    ) -> None:
        item_payload['is_manual'] = False
        auth_telegram_api_client.post(item_list_url(str(shopping_list.id)), data=item_payload, format='json')
        item = ShoppingListItem.objects.get(shopping_list=shopping_list)
        assert item.is_manual is True

    def test_owner_is_set_from_request_user(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        item_payload: dict,
        telegram_user: User,
    ) -> None:
        auth_telegram_api_client.post(item_list_url(str(shopping_list.id)), data=item_payload, format='json')
        item = ShoppingListItem.objects.get(shopping_list=shopping_list)
        assert item.owner == telegram_user

    def test_shopping_list_is_set_from_url(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        item_payload: dict,
    ) -> None:
        auth_telegram_api_client.post(item_list_url(str(shopping_list.id)), data=item_payload, format='json')
        item = ShoppingListItem.objects.get(shopping_list=shopping_list)
        assert item.shopping_list == shopping_list

    def test_amount_is_stored_correctly(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        item_payload: dict,
    ) -> None:
        auth_telegram_api_client.post(item_list_url(str(shopping_list.id)), data=item_payload, format='json')
        item = ShoppingListItem.objects.get(shopping_list=shopping_list)
        assert item.amount == Decimal('150.000')

    def test_foreign_ingredient_is_rejected(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        ingredient_user: Ingredient,
        another_telegram_user: User,
    ) -> None:
        """ingredient_user belongs to telegram_user, but we'll simulate foreign by using another user's ingredient."""
        # ingredient_user fixture creates ingredient owned by telegram_user, which IS accessible.
        # Create an ingredient owned by another_telegram_user that should be rejected.
        foreign_ingredient = Ingredient.objects.create(
            name='foreign-ingredient',
            owner=another_telegram_user,
            base_unit=ingredient_user.base_unit,
            category=ingredient_user.category,
        )
        payload = {'ingredient': str(foreign_ingredient.id), 'amount': '10.000'}
        response = auth_telegram_api_client.post(item_list_url(str(shopping_list.id)), data=payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_nonexistent_ingredient_uuid_returns_400(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
    ) -> None:
        payload = {'ingredient': str(uuid.uuid4()), 'amount': '10.000'}
        response = auth_telegram_api_client.post(item_list_url(str(shopping_list.id)), data=payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_amount_returns_400(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        item_payload: dict,
    ) -> None:
        item_payload.pop('manual_amount')
        response = auth_telegram_api_client.post(item_list_url(str(shopping_list.id)), data=item_payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_ingredient_returns_400(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        item_payload: dict,
    ) -> None:
        item_payload.pop('ingredient')
        response = auth_telegram_api_client.post(item_list_url(str(shopping_list.id)), data=item_payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_response_uses_read_serializer(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        item_payload: dict,
    ) -> None:
        """Response should contain nested ingredient object, not just a UUID."""
        response = auth_telegram_api_client.post(item_list_url(str(shopping_list.id)), data=item_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert isinstance(response.data['ingredient'], dict)


class TestShoppingListItemViewSetPartialUpdate:
    def test_anon_client_cannot_patch(
        self,
        api_client: APIClient,
        shopping_list: ShoppingList,
        manual_shopping_list_item: ShoppingListItem,
    ) -> None:
        response = api_client.patch(
            item_detail_url(str(shopping_list.id), str(manual_shopping_list_item.id)),
            data={'amount': '200.000'},
            format='json',
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_another_user_cannot_patch(
        self,
        auth_another_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        manual_shopping_list_item: ShoppingListItem,
    ) -> None:
        response = auth_another_telegram_api_client.patch(
            item_detail_url(str(shopping_list.id), str(manual_shopping_list_item.id)),
            data={'amount': '200.000'},
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_owner_can_patch_amount(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        manual_shopping_list_item: ShoppingListItem,
    ) -> None:
        response = auth_telegram_api_client.patch(
            item_detail_url(str(shopping_list.id), str(manual_shopping_list_item.id)),
            data={'manual_amount': '200.000'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        manual_shopping_list_item.refresh_from_db()
        assert manual_shopping_list_item.amount == Decimal('200.000')

    def test_is_manual_remains_true_after_patch(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        manual_shopping_list_item: ShoppingListItem,
    ) -> None:
        auth_telegram_api_client.patch(
            item_detail_url(str(shopping_list.id), str(manual_shopping_list_item.id)),
            data={'amount': '200.000'},
            format='json',
        )
        manual_shopping_list_item.refresh_from_db()
        assert manual_shopping_list_item.is_manual is True

    def test_patch_response_uses_read_serializer(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        manual_shopping_list_item: ShoppingListItem,
    ) -> None:
        response = auth_telegram_api_client.patch(
            item_detail_url(str(shopping_list.id), str(manual_shopping_list_item.id)),
            data={'amount': '200.000'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data['ingredient'], dict)


class TestShoppingListItemViewSetDestroy:
    def test_anon_client_cannot_delete(
        self,
        api_client: APIClient,
        shopping_list: ShoppingList,
        manual_shopping_list_item: ShoppingListItem,
    ) -> None:
        response = api_client.delete(item_detail_url(str(shopping_list.id), str(manual_shopping_list_item.id)))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_another_user_cannot_delete(
        self,
        auth_another_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        manual_shopping_list_item: ShoppingListItem,
    ) -> None:
        response = auth_another_telegram_api_client.delete(
            item_detail_url(str(shopping_list.id), str(manual_shopping_list_item.id))
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_owner_can_delete_item(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        manual_shopping_list_item: ShoppingListItem,
    ) -> None:
        response = auth_telegram_api_client.delete(
            item_detail_url(str(shopping_list.id), str(manual_shopping_list_item.id))
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ShoppingListItem.objects.filter(id=manual_shopping_list_item.id).exists()
