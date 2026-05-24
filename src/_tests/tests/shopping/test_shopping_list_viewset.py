import pytest

import uuid
from datetime import date, timedelta

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.planning.models import CookingEvent
from apps.shopping.api.serializers.shopping_list import ShoppingListSerializer
from apps.shopping.models import ShoppingList, ShoppingListItem
from apps.users.models import User

LIST_URL = reverse('api_v1:shopping:shopping:shopping-list-list')


def detail_url(shopping_list_id: str) -> str:
    return reverse(
        'api_v1:shopping:shopping:shopping-list-detail',
        kwargs={'shopping_list_id': shopping_list_id},
    )


def recalculate_url(shopping_list_id: str) -> str:
    return reverse(
        'api_v1:shopping:shopping:shopping-list-recalculate',
        kwargs={'shopping_list_id': shopping_list_id},
    )


@pytest.fixture
def shopping_list_payload(week_start: date, week_end: date) -> dict:
    return {
        'name': 'Weekly groceries',
        'date_from': str(week_start),
        'date_to': str(week_end),
    }


class TestShoppingListViewSetList:
    def test_anon_client_cannot_list(self, api_client: APIClient) -> None:
        response = api_client.get(LIST_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_client_gets_empty_list_when_no_shopping_lists(
        self, auth_telegram_api_client: APIClient
    ) -> None:
        response = auth_telegram_api_client.get(LIST_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []

    def test_authenticated_client_gets_own_shopping_lists(
        self, auth_telegram_api_client: APIClient, shopping_list: ShoppingList
    ) -> None:
        response = auth_telegram_api_client.get(LIST_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'] == ShoppingListSerializer([shopping_list], many=True).data

    @pytest.mark.usefixtures('shopping_list')
    def test_does_not_return_another_users_shopping_lists(self, auth_another_telegram_api_client: APIClient) -> None:
        response = auth_another_telegram_api_client.get(LIST_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []

    def test_filter_by_name_returns_matching_list(
        self, auth_telegram_api_client: APIClient, shopping_list: ShoppingList
    ) -> None:
        response = auth_telegram_api_client.get(LIST_URL, data={'name__icontains': shopping_list.name[:4]})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_filter_by_name_returns_empty_when_no_match(
        self, auth_telegram_api_client: APIClient, shopping_list: ShoppingList
    ) -> None:
        response = auth_telegram_api_client.get(LIST_URL, data={'name': 'no-such-list'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0


class TestShoppingListViewSetRetrieve:
    def test_anon_client_cannot_retrieve(self, api_client: APIClient, shopping_list: ShoppingList) -> None:
        response = api_client.get(detail_url(str(shopping_list.id)))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_owner_can_retrieve_own_shopping_list(
        self, auth_telegram_api_client: APIClient, shopping_list: ShoppingList
    ) -> None:
        response = auth_telegram_api_client.get(detail_url(str(shopping_list.id)))
        assert response.status_code == status.HTTP_200_OK
        assert response.data == ShoppingListSerializer(shopping_list).data

    def test_another_user_cannot_retrieve_shopping_list(
        self, auth_another_telegram_api_client: APIClient, shopping_list: ShoppingList
    ) -> None:
        response = auth_another_telegram_api_client.get(detail_url(str(shopping_list.id)))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nonexistent_id_returns_404(self, auth_telegram_api_client: APIClient) -> None:
        response = auth_telegram_api_client.get(detail_url(str(uuid.uuid4())))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_response_contains_expected_fields(
        self, auth_telegram_api_client: APIClient, shopping_list: ShoppingList
    ) -> None:
        response = auth_telegram_api_client.get(detail_url(str(shopping_list.id)))
        assert response.status_code == status.HTTP_200_OK
        assert set(response.data.keys()) >= {'id', 'name', 'date_from', 'date_to'}


class TestShoppingListViewSetCreate:
    def test_anon_client_cannot_create(self, api_client: APIClient, shopping_list_payload: dict) -> None:
        response = api_client.post(LIST_URL, data=shopping_list_payload, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_valid_data_creates_shopping_list(
        self, auth_telegram_api_client: APIClient, shopping_list_payload: dict
    ) -> None:
        response = auth_telegram_api_client.post(LIST_URL, data=shopping_list_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert ShoppingList.objects.count() == 1

    def test_owner_is_set_from_request_user(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list_payload: dict,
        telegram_user: User,
    ) -> None:
        auth_telegram_api_client.post(LIST_URL, data=shopping_list_payload, format='json')
        created = ShoppingList.objects.get()
        assert created.owner == telegram_user

    def test_missing_name_returns_400(self, auth_telegram_api_client: APIClient, shopping_list_payload: dict) -> None:
        shopping_list_payload.pop('name')
        response = auth_telegram_api_client.post(LIST_URL, data=shopping_list_payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_date_from_returns_400(
        self, auth_telegram_api_client: APIClient, shopping_list_payload: dict
    ) -> None:
        shopping_list_payload.pop('date_from')
        response = auth_telegram_api_client.post(LIST_URL, data=shopping_list_payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_triggers_recalculation_of_items(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list_payload: dict,
        cooking_event_with_ingredients: CookingEvent,
    ) -> None:
        """Creating a shopping list should auto-populate non-manual items from cooking events."""
        response = auth_telegram_api_client.post(LIST_URL, data=shopping_list_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        created = ShoppingList.objects.get()
        assert ShoppingListItem.objects.filter(shopping_list=created, is_manual=False).exists()

    def test_create_without_cooking_events_creates_no_items(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list_payload: dict,
    ) -> None:
        auth_telegram_api_client.post(LIST_URL, data=shopping_list_payload, format='json')
        assert ShoppingListItem.objects.count() == 0


class TestShoppingListViewSetPartialUpdate:
    def test_anon_client_cannot_patch(self, api_client: APIClient, shopping_list: ShoppingList) -> None:
        response = api_client.patch(detail_url(str(shopping_list.id)), data={'name': 'new'}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_owner_can_patch_name(self, auth_telegram_api_client: APIClient, shopping_list: ShoppingList) -> None:
        response = auth_telegram_api_client.patch(
            detail_url(str(shopping_list.id)), data={'name': 'Updated name'}, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        shopping_list.refresh_from_db()
        assert shopping_list.name == 'Updated name'

    def test_another_user_cannot_patch(
        self, auth_another_telegram_api_client: APIClient, shopping_list: ShoppingList
    ) -> None:
        response = auth_another_telegram_api_client.patch(
            detail_url(str(shopping_list.id)), data={'name': 'hack'}, format='json'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_name_only_does_not_recalculate_items(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        shopping_list_item: ShoppingListItem,
        cooking_event_with_ingredients: CookingEvent,
    ) -> None:
        """
        When PATCH contains only 'name', not_recalculated_fields={'name'} means
        update_fields - {'name'} == empty → recalculation is skipped.
        The existing item must remain unchanged.
        """
        original_amount = shopping_list_item.amount
        auth_telegram_api_client.patch(detail_url(str(shopping_list.id)), data={'name': 'Renamed'}, format='json')
        shopping_list_item.refresh_from_db()
        assert shopping_list_item.amount == original_amount

    def test_patch_date_range_triggers_recalculation(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        cooking_event_with_ingredients: CookingEvent,
        week_start: date,
        week_end: date,
    ) -> None:
        """
        When PATCH includes date_from/date_to, recalculation must run and create items.
        """
        assert ShoppingListItem.objects.filter(shopping_list=shopping_list, is_manual=False).count() == 0

        new_date_from = week_start - timedelta(days=1)
        auth_telegram_api_client.patch(
            detail_url(str(shopping_list.id)),
            data={'date_from': str(new_date_from)},
            format='json',
        )
        assert ShoppingListItem.objects.filter(shopping_list=shopping_list, is_manual=False).exists()

    def test_patch_name_and_date_triggers_recalculation(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        cooking_event_with_ingredients: CookingEvent,
        week_start: date,
    ) -> None:
        """When both name and a date field are patched, recalculation must still run."""
        assert ShoppingListItem.objects.filter(shopping_list=shopping_list, is_manual=False).count() == 0

        auth_telegram_api_client.patch(
            detail_url(str(shopping_list.id)),
            data={'name': 'New name', 'date_from': str(week_start)},
            format='json',
        )
        assert ShoppingListItem.objects.filter(shopping_list=shopping_list, is_manual=False).exists()


class TestShoppingListViewSetDestroy:
    def test_anon_client_cannot_delete(self, api_client: APIClient, shopping_list: ShoppingList) -> None:
        response = api_client.delete(detail_url(str(shopping_list.id)))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_owner_can_delete_own_shopping_list(
        self, auth_telegram_api_client: APIClient, shopping_list: ShoppingList
    ) -> None:
        response = auth_telegram_api_client.delete(detail_url(str(shopping_list.id)))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ShoppingList.objects.filter(id=shopping_list.id).exists()

    def test_another_user_cannot_delete(
        self, auth_another_telegram_api_client: APIClient, shopping_list: ShoppingList
    ) -> None:
        response = auth_another_telegram_api_client.delete(detail_url(str(shopping_list.id)))
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert ShoppingList.objects.filter(id=shopping_list.id).exists()

    def test_nonexistent_id_returns_404(self, auth_telegram_api_client: APIClient) -> None:
        response = auth_telegram_api_client.delete(detail_url(str(uuid.uuid4())))
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestShoppingListViewSetRecalculate:
    def test_anon_client_cannot_recalculate(self, api_client: APIClient, shopping_list: ShoppingList) -> None:
        response = api_client.post(recalculate_url(str(shopping_list.id)))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_owner_can_trigger_recalculate(
        self, auth_telegram_api_client: APIClient, shopping_list: ShoppingList
    ) -> None:
        response = auth_telegram_api_client.post(recalculate_url(str(shopping_list.id)))
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {'detail': 'Shopping list recalculated successfully.'}

    def test_another_user_cannot_recalculate(
        self, auth_another_telegram_api_client: APIClient, shopping_list: ShoppingList
    ) -> None:
        response = auth_another_telegram_api_client.post(recalculate_url(str(shopping_list.id)))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nonexistent_id_returns_404(self, auth_telegram_api_client: APIClient) -> None:
        response = auth_telegram_api_client.post(recalculate_url(str(uuid.uuid4())))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_recalculate_creates_items_from_cooking_events(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        cooking_event_with_ingredients: CookingEvent,
    ) -> None:
        assert ShoppingListItem.objects.filter(shopping_list=shopping_list, is_manual=False).count() == 0

        auth_telegram_api_client.post(recalculate_url(str(shopping_list.id)))

        assert ShoppingListItem.objects.filter(shopping_list=shopping_list, is_manual=False).exists()

    def test_recalculate_preserves_manual_items(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        manual_shopping_list_item: ShoppingListItem,
    ) -> None:
        auth_telegram_api_client.post(recalculate_url(str(shopping_list.id)))
        assert ShoppingListItem.objects.filter(id=manual_shopping_list_item.id, is_manual=True).exists()

    def test_recalculate_removes_stale_non_manual_items(
        self,
        auth_telegram_api_client: APIClient,
        shopping_list: ShoppingList,
        shopping_list_item: ShoppingListItem,
    ) -> None:
        """Non-manual item with no matching cooking event should be deleted on recalculation."""
        auth_telegram_api_client.post(recalculate_url(str(shopping_list.id)))
        assert not ShoppingListItem.objects.filter(id=shopping_list_item.id).exists()
