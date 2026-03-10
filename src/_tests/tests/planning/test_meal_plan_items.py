
import uuid
from datetime import timedelta

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from pytest_django.fixtures import DjangoAssertNumQueries

from _tests.fixtures.planning import WEEK_START
from apps.dishes.models import Dish
from apps.planning.models import CookingEvent, MealPlanItem
from apps.users.models import User


class TestMealPlanItemViewSetCreate:
    list_url = reverse('api_v1:planning:cooking:meal-plan-item-list')

    def test_anon_client_cannot_create(self, api_client: APIClient, meal_plan_item_payload: dict) -> None:
        response = api_client.post(self.list_url, data=meal_plan_item_payload, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_on_list_not_allowed(self, auth_telegram_api_client: APIClient) -> None:
        response = auth_telegram_api_client.get(self.list_url)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_put_on_list_not_allowed(self, auth_telegram_api_client: APIClient, meal_plan_item_payload: dict) -> None:
        response = auth_telegram_api_client.put(self.list_url, data=meal_plan_item_payload, format='json')
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_valid_payload_creates_meal_plan_item(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item_payload: dict,
    ) -> None:
        response = auth_telegram_api_client.post(self.list_url, data=meal_plan_item_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert MealPlanItem.objects.count() == 1

    def test_owner_is_set_from_request_user_not_from_body(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item_payload: dict,
        telegram_user: User,
        another_telegram_user: User,
    ) -> None:
        # Passing a different owner in the body must be ignored because owner is HiddenField
        meal_plan_item_payload['owner'] = str(another_telegram_user.id)
        auth_telegram_api_client.post(self.list_url, data=meal_plan_item_payload, format='json')
        item = MealPlanItem.objects.get()
        assert item.owner == telegram_user

    def test_is_manual_is_always_true_regardless_of_body(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item_payload: dict,
    ) -> None:
        # is_manual is HiddenField(default=True) — body value is completely ignored
        meal_plan_item_payload['is_manual'] = False
        auth_telegram_api_client.post(self.list_url, data=meal_plan_item_payload, format='json')
        item = MealPlanItem.objects.get()
        assert item.is_manual is True

    def test_cooking_event_is_null_after_manual_create(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item_payload: dict,
    ) -> None:
        # cooking_event is read_only on create — always null for manually created items
        meal_plan_item_payload['cooking_event'] = str(uuid.uuid4())
        auth_telegram_api_client.post(self.list_url, data=meal_plan_item_payload, format='json')
        item = MealPlanItem.objects.get()
        assert item.cooking_event is None

    def test_dish_in_response_is_uuid_not_nested_object(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item_payload: dict,
    ) -> None:
        # MealPlanItemCreateSerializer has no DishReadSerializer override —
        # dish is returned as a UUID (not a nested dict), unlike CookingEventSerializer
        response = auth_telegram_api_client.post(self.list_url, data=meal_plan_item_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert not isinstance(response.data['dish'], dict)

    def test_position_defaults_to_100_when_not_provided(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item_payload: dict,
    ) -> None:
        del meal_plan_item_payload['position']
        auth_telegram_api_client.post(self.list_url, data=meal_plan_item_payload, format='json')
        item = MealPlanItem.objects.get()
        assert item.position == 100

    def test_position_can_be_set_explicitly(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item_payload: dict,
    ) -> None:
        meal_plan_item_payload['position'] = 5
        auth_telegram_api_client.post(self.list_url, data=meal_plan_item_payload, format='json')
        item = MealPlanItem.objects.get()
        assert item.position == 5

    def test_date_is_saved_correctly(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item_payload: dict,
    ) -> None:
        auth_telegram_api_client.post(self.list_url, data=meal_plan_item_payload, format='json')
        item = MealPlanItem.objects.get()
        assert str(item.date) == meal_plan_item_payload['date']

    def test_missing_dish_returns_400(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item_payload: dict,
    ) -> None:
        del meal_plan_item_payload['dish']
        response = auth_telegram_api_client.post(self.list_url, data=meal_plan_item_payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_date_returns_400(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item_payload: dict,
    ) -> None:
        del meal_plan_item_payload['date']
        response = auth_telegram_api_client.post(self.list_url, data=meal_plan_item_payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_nonexistent_dish_uuid_returns_400(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item_payload: dict,
    ) -> None:
        meal_plan_item_payload['dish'] = str(uuid.uuid4())
        response = auth_telegram_api_client.post(self.list_url, data=meal_plan_item_payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_date_format_returns_400(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item_payload: dict,
    ) -> None:
        meal_plan_item_payload['date'] = 'not-a-date'
        response = auth_telegram_api_client.post(self.list_url, data=meal_plan_item_payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestMealPlanItemViewSetPartialUpdate:
    def get_url(self, item_id: str) -> str:
        return reverse(
            'api_v1:planning:cooking:meal-plan-item-detail',
            kwargs={'meal_plan_item_id': item_id},
        )

    def test_anon_client_cannot_patch(self, api_client: APIClient, meal_plan_item: MealPlanItem) -> None:
        response = api_client.patch(self.get_url(str(meal_plan_item.id)), data={}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_another_user_cannot_patch_returns_404(
        self,
        auth_another_telegram_api_client: APIClient,
        meal_plan_item: MealPlanItem,
    ) -> None:
        # queryset is filtered to owner, so another user sees no object → 404, not 403
        response = auth_another_telegram_api_client.patch(
            self.get_url(str(meal_plan_item.id)), data={'position': 5}, format='json'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_owner_can_patch_own_item(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item: MealPlanItem,
    ) -> None:
        response = auth_telegram_api_client.patch(
            self.get_url(str(meal_plan_item.id)), data={'position': 5}, format='json'
        )
        assert response.status_code == status.HTTP_200_OK

    def test_nonexistent_id_returns_404(self, auth_telegram_api_client: APIClient) -> None:
        response = auth_telegram_api_client.patch(self.get_url(str(uuid.uuid4())), data={'position': 5}, format='json')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_put_on_detail_not_allowed(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item: MealPlanItem,
    ) -> None:
        response = auth_telegram_api_client.put(self.get_url(str(meal_plan_item.id)), data={}, format='json')
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_get_on_detail_not_allowed(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item: MealPlanItem,
    ) -> None:
        response = auth_telegram_api_client.get(self.get_url(str(meal_plan_item.id)))
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_can_update_date(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item: MealPlanItem,
    ) -> None:
        new_date = WEEK_START + timedelta(days=3)
        response = auth_telegram_api_client.patch(
            self.get_url(str(meal_plan_item.id)), data={'date': str(new_date)}, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        meal_plan_item.refresh_from_db()
        assert meal_plan_item.date == new_date

    def test_can_update_position(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item: MealPlanItem,
    ) -> None:
        response = auth_telegram_api_client.patch(
            self.get_url(str(meal_plan_item.id)), data={'position': 42}, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        meal_plan_item.refresh_from_db()
        assert meal_plan_item.position == 42

    def test_can_update_dish(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item: MealPlanItem,
        dish_user: Dish,
    ) -> None:
        response = auth_telegram_api_client.patch(
            self.get_url(str(meal_plan_item.id)), data={'dish': str(dish_user.id)}, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        meal_plan_item.refresh_from_db()
        assert meal_plan_item.dish == dish_user

    def test_partial_patch_single_field_works(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item: MealPlanItem,
    ) -> None:
        # Only one field at a time — other fields must remain unchanged
        original_date = meal_plan_item.date
        response = auth_telegram_api_client.patch(
            self.get_url(str(meal_plan_item.id)), data={'position': 7}, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        meal_plan_item.refresh_from_db()
        assert meal_plan_item.date == original_date
        assert meal_plan_item.position == 7

    def test_owner_cannot_be_changed_via_patch(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item: MealPlanItem,
        telegram_user: User,
        another_telegram_user: User,
    ) -> None:
        # owner is read_only in MealPlanItemUpdateSerializer — body value ignored
        response = auth_telegram_api_client.patch(
            self.get_url(str(meal_plan_item.id)),
            data={'owner': str(another_telegram_user.id)},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        meal_plan_item.refresh_from_db()
        assert meal_plan_item.owner == telegram_user

    def test_cooking_event_cannot_be_changed_via_patch(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item: MealPlanItem,
    ) -> None:
        # cooking_event is read_only in MealPlanItemUpdateSerializer — body value ignored
        original_event = meal_plan_item.cooking_event
        response = auth_telegram_api_client.patch(
            self.get_url(str(meal_plan_item.id)),
            data={'cooking_event': str(uuid.uuid4())},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        meal_plan_item.refresh_from_db()
        assert meal_plan_item.cooking_event == original_event

    def test_is_manual_cannot_be_changed_via_patch(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item: MealPlanItem,
    ) -> None:
        # is_manual is read_only in MealPlanItemUpdateSerializer — body value ignored
        assert meal_plan_item.is_manual is True
        response = auth_telegram_api_client.patch(
            self.get_url(str(meal_plan_item.id)),
            data={'is_manual': False},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        meal_plan_item.refresh_from_db()
        assert meal_plan_item.is_manual is True

    def test_dish_in_response_is_uuid_not_nested_object(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item: MealPlanItem,
    ) -> None:
        # MealPlanItemUpdateSerializer does not override dish — returns UUID (not dict), unlike MealPlanItemSerializer
        response = auth_telegram_api_client.patch(
            self.get_url(str(meal_plan_item.id)), data={'position': 3}, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert not isinstance(response.data['dish'], dict)

    def test_is_manual_appears_in_update_response(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item: MealPlanItem,
    ) -> None:
        # Unlike create (HiddenField), update uses regular read_only field — visible in output
        response = auth_telegram_api_client.patch(
            self.get_url(str(meal_plan_item.id)), data={'position': 3}, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'is_manual' in response.data
        assert response.data['is_manual'] is True

    def test_cooking_event_on_linked_item_remains_after_patch(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_with_meal_plan_items: CookingEvent,
        telegram_user: User,
    ) -> None:
        event = cooking_event_with_meal_plan_items
        item = MealPlanItem.objects.filter(cooking_event=event).first()
        assert item is not None
        response = auth_telegram_api_client.patch(self.get_url(str(item.id)), data={'position': 99}, format='json')
        assert response.status_code == status.HTTP_200_OK
        item.refresh_from_db()
        assert item.cooking_event == event


class TestMealPlanItemViewSetDelete:
    def get_url(self, item_id: str) -> str:
        return reverse(
            'api_v1:planning:cooking:meal-plan-item-detail',
            kwargs={'meal_plan_item_id': item_id},
        )

    def test_anon_client_cannot_delete(self, api_client: APIClient, meal_plan_item: MealPlanItem) -> None:
        response = api_client.delete(self.get_url(str(meal_plan_item.id)))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_another_user_cannot_delete_returns_404(
        self,
        auth_another_telegram_api_client: APIClient,
        meal_plan_item: MealPlanItem,
    ) -> None:
        # queryset is filtered to owner → 404, not 403
        response = auth_another_telegram_api_client.delete(self.get_url(str(meal_plan_item.id)))
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert MealPlanItem.objects.filter(pk=meal_plan_item.pk).exists()

    def test_owner_can_delete_own_item(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item: MealPlanItem,
    ) -> None:
        response = auth_telegram_api_client.delete(self.get_url(str(meal_plan_item.id)))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not MealPlanItem.objects.filter(pk=meal_plan_item.pk).exists()

    def test_nonexistent_id_returns_404(self, auth_telegram_api_client: APIClient) -> None:
        response = auth_telegram_api_client.delete(self.get_url(str(uuid.uuid4())))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_on_detail_not_allowed(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item: MealPlanItem,
    ) -> None:
        response = auth_telegram_api_client.get(self.get_url(str(meal_plan_item.id)))
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_deleting_manual_item_does_not_affect_cooking_event(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_with_meal_plan_items: CookingEvent,
        telegram_user: User,
        dish_global: Dish,
    ) -> None:
        # Create a separate manual item linked to no event; cooking_event must survive its deletion
        manual_item = MealPlanItem.objects.create(
            owner=telegram_user,
            dish=dish_global,
            date=WEEK_START,
            is_manual=True,
            position=50,
        )
        event = cooking_event_with_meal_plan_items
        items_before = MealPlanItem.objects.filter(cooking_event=event).count()
        auth_telegram_api_client.delete(self.get_url(str(manual_item.id)))
        assert CookingEvent.objects.filter(pk=event.pk).exists()
        assert MealPlanItem.objects.filter(cooking_event=event).count() == items_before

    def test_deleting_item_linked_to_cooking_event_removes_only_that_item(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_with_meal_plan_items: CookingEvent,
        telegram_user: User,
    ) -> None:
        event = cooking_event_with_meal_plan_items
        items_before = MealPlanItem.objects.filter(cooking_event=event).count()
        item = MealPlanItem.objects.filter(cooking_event=event).first()
        assert item is not None
        response = auth_telegram_api_client.delete(self.get_url(str(item.id)))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        # Only the targeted item was removed; cooking_event and other items remain
        assert CookingEvent.objects.filter(pk=event.pk).exists()
        assert MealPlanItem.objects.filter(cooking_event=event).count() == items_before - 1


class TestMealPlanItemViewSetQueryCount:
    list_url = reverse('api_v1:planning:cooking:meal-plan-item-list')

    def get_detail_url(self, item_id: str) -> str:
        return reverse(
            'api_v1:planning:cooking:meal-plan-item-detail',
            kwargs={'meal_plan_item_id': item_id},
        )

    def test_create_query_count(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item_payload: dict,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        with django_assert_num_queries(3):
            response = auth_telegram_api_client.post(self.list_url, data=meal_plan_item_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_patch_query_count(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item: MealPlanItem,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        with django_assert_num_queries(4):
            response = auth_telegram_api_client.patch(
                self.get_detail_url(str(meal_plan_item.id)),
                data={'position': 10},
                format='json',
            )
        assert response.status_code == status.HTTP_200_OK

    def test_delete_query_count(
        self,
        auth_telegram_api_client: APIClient,
        meal_plan_item: MealPlanItem,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        with django_assert_num_queries(4):
            response = auth_telegram_api_client.delete(self.get_detail_url(str(meal_plan_item.id)))
        assert response.status_code == status.HTTP_204_NO_CONTENT
