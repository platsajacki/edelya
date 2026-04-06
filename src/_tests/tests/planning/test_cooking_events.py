import pytest

import uuid
from datetime import date, timedelta

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from pytest_django.fixtures import DjangoAssertNumQueries

from _tests.fixtures.planning import WEEK_START
from apps.dishes.models import Dish
from apps.planning.api.serializers.cooking import CookingEventSerializer
from apps.planning.models import CookingEvent, MealPlanItem
from apps.users.models import User


class TestCookingEventViewSetList:
    list_url = reverse('api_v1:planning:cooking:cooking-event-list')

    def test_anon_client_cannot_get_list(self, api_client: APIClient) -> None:
        response = api_client.get(self.list_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_client_gets_empty_list_when_no_events(self, auth_telegram_api_client: APIClient) -> None:
        response = auth_telegram_api_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []

    def test_authenticated_client_gets_own_events(
        self, auth_telegram_api_client: APIClient, cooking_event: CookingEvent
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'] == CookingEventSerializer([cooking_event], many=True).data

    @pytest.mark.usefixtures('another_user_cooking_event')
    def test_does_not_return_another_users_events(self, auth_telegram_api_client: APIClient) -> None:
        response = auth_telegram_api_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []

    def test_list_ordered_by_cooking_date_then_created_at(
        self,
        auth_telegram_api_client: APIClient,
        telegram_user: User,
        dish_global: Dish,
    ) -> None:
        earlier = CookingEvent.objects.create(
            owner=telegram_user,
            dish=dish_global,
            cooking_date=date(2026, 4, 1),
        )
        later = CookingEvent.objects.create(
            owner=telegram_user,
            dish=dish_global,
            cooking_date=date(2026, 5, 1),
        )
        response = auth_telegram_api_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        ids = [item['id'] for item in response.data['results']]
        assert ids.index(str(earlier.id)) < ids.index(str(later.id))

    @pytest.mark.usefixtures('another_user_cooking_event')
    def test_only_own_events_returned_when_multiple_users_have_events(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event: CookingEvent,
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'] == CookingEventSerializer([cooking_event], many=True).data


class TestCookingEventViewSetRetrieve:
    def get_url(self, cooking_event_id: str) -> str:
        return reverse(
            'api_v1:planning:cooking:cooking-event-detail',
            kwargs={'cooking_event_id': cooking_event_id},
        )

    def test_anon_client_cannot_retrieve(self, api_client: APIClient, cooking_event: CookingEvent) -> None:
        response = api_client.get(self.get_url(str(cooking_event.id)))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_owner_can_retrieve_own_event(
        self, auth_telegram_api_client: APIClient, cooking_event: CookingEvent
    ) -> None:
        response = auth_telegram_api_client.get(self.get_url(str(cooking_event.id)))
        assert response.status_code == status.HTTP_200_OK
        assert response.data == CookingEventSerializer(cooking_event).data

    def test_another_user_cannot_retrieve_event(
        self,
        auth_another_telegram_api_client: APIClient,
        cooking_event: CookingEvent,
    ) -> None:
        response = auth_another_telegram_api_client.get(self.get_url(str(cooking_event.id)))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nonexistent_id_returns_404(self, auth_telegram_api_client: APIClient) -> None:
        response = auth_telegram_api_client.get(self.get_url(str(uuid.uuid4())))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_response_contains_nested_dish_object(
        self, auth_telegram_api_client: APIClient, cooking_event: CookingEvent
    ) -> None:
        response = auth_telegram_api_client.get(self.get_url(str(cooking_event.id)))
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data['dish'], dict)


class TestCookingEventViewSetCreate:
    list_url = reverse('api_v1:planning:cooking:cooking-event-list')

    def test_anon_client_cannot_create(self, api_client: APIClient, cooking_event_payload: dict) -> None:
        response = api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_valid_data_creates_cooking_event(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
    ) -> None:
        response = auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert CookingEvent.objects.count() == 1

    def test_creates_meal_plan_items_equal_to_duration_days(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
    ) -> None:
        cooking_event_payload['eat_dates'] = [str(WEEK_START + timedelta(days=i)) for i in range(4)]
        auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert MealPlanItem.objects.count() == 4

    def test_meal_plan_item_dates_start_from_start_eating_date(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
    ) -> None:
        cooking_event_payload['eat_dates'] = [str(WEEK_START + timedelta(days=i)) for i in range(3)]
        auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        dates = sorted(MealPlanItem.objects.values_list('date', flat=True))
        expected = [WEEK_START + timedelta(days=i) for i in range(3)]
        assert list(dates) == expected

    def test_meal_plan_items_linked_to_cooking_event(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
    ) -> None:
        auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        event = CookingEvent.objects.get()
        assert MealPlanItem.objects.filter(cooking_event=event).count() == len(cooking_event_payload['eat_dates'])

    def test_meal_plan_items_are_not_manual(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
    ) -> None:
        auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert not MealPlanItem.objects.filter(is_manual=True).exists()

    def test_meal_plan_items_belong_to_request_user(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
        telegram_user: User,
    ) -> None:
        auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert not MealPlanItem.objects.exclude(owner=telegram_user).exists()

    def test_owner_is_set_from_request_user_not_from_body(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
        telegram_user: User,
        another_telegram_user: User,
    ) -> None:
        # Attempting to pass a different owner in body should be ignored
        cooking_event_payload['owner'] = str(another_telegram_user.id)
        auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        event = CookingEvent.objects.get()
        assert event.owner == telegram_user

    def test_start_eating_date_before_cooking_date_returns_400(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
    ) -> None:
        cooking_event_payload['eat_dates'] = [str(WEEK_START - timedelta(days=1))]
        response = auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_start_eating_date_equal_to_cooking_date_is_valid(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
    ) -> None:
        cooking_event_payload['eat_dates'] = [str(WEEK_START)]
        response = auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_start_eating_date_after_cooking_date_is_valid(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
    ) -> None:
        cooking_event_payload['eat_dates'] = [str(WEEK_START + timedelta(days=2))]
        response = auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_duration_days_zero_returns_400(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
    ) -> None:
        cooking_event_payload['eat_dates'] = []
        response = auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_duration_days_31_returns_400(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
    ) -> None:
        cooking_event_payload['eat_dates'] = [str(WEEK_START + timedelta(days=i)) for i in range(31)]
        response = auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_duration_days_1_creates_exactly_one_meal_plan_item(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
    ) -> None:
        cooking_event_payload['eat_dates'] = [str(WEEK_START)]
        response = auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert MealPlanItem.objects.count() == 1

    def test_duration_days_30_creates_exactly_30_meal_plan_items(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
    ) -> None:
        cooking_event_payload['eat_dates'] = [str(WEEK_START + timedelta(days=i)) for i in range(30)]
        response = auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert MealPlanItem.objects.count() == 30

    def test_missing_dish_returns_400(self, auth_telegram_api_client: APIClient, cooking_event_payload: dict) -> None:
        del cooking_event_payload['dish']
        response = auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_cooking_date_returns_400(
        self, auth_telegram_api_client: APIClient, cooking_event_payload: dict
    ) -> None:
        del cooking_event_payload['cooking_date']
        response = auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_start_eating_date_returns_400(
        self, auth_telegram_api_client: APIClient, cooking_event_payload: dict
    ) -> None:
        del cooking_event_payload['eat_dates']
        response = auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_duration_days_returns_400(
        self, auth_telegram_api_client: APIClient, cooking_event_payload: dict
    ) -> None:
        cooking_event_payload['eat_dates'] = ['invalid-date']
        response = auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_response_uses_read_serializer_with_nested_dish(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
        dish_global: Dish,
    ) -> None:
        # CookingEventWriteSerializer.to_representation returns CookingEventSerializer output
        response = auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert isinstance(response.data['dish'], dict)

    def test_notes_defaults_to_empty_string_when_not_provided(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
    ) -> None:
        response = auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['notes'] == ''

    def test_notes_can_be_set_on_create(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
    ) -> None:
        cooking_event_payload['notes'] = 'Add extra salt'
        response = auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['notes'] == 'Add extra salt'

    def test_response_contains_color_field(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
    ) -> None:
        response = auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert 'color' in response.data
        assert response.data['color']

    def test_all_meal_plan_items_inherit_cooking_event_color(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_payload: dict,
    ) -> None:
        response = auth_telegram_api_client.post(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        event_color = response.data['color']
        items_colors = {item['color'] for item in response.data['meal_plan_items']}
        assert items_colors == {event_color}

    def test_put_method_not_allowed_on_list(
        self, auth_telegram_api_client: APIClient, cooking_event_payload: dict
    ) -> None:
        response = auth_telegram_api_client.put(self.list_url, data=cooking_event_payload, format='json')
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestCookingEventViewSetPartialUpdate:
    def get_url(self, cooking_event_id: str) -> str:
        return reverse(
            'api_v1:planning:cooking:cooking-event-detail',
            kwargs={'cooking_event_id': cooking_event_id},
        )

    def test_anon_client_cannot_patch(self, api_client: APIClient, cooking_event: CookingEvent) -> None:
        response = api_client.patch(self.get_url(str(cooking_event.id)), data={}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_owner_can_patch_own_event(self, auth_telegram_api_client: APIClient, cooking_event: CookingEvent) -> None:
        response = auth_telegram_api_client.patch(
            self.get_url(str(cooking_event.id)),
            data={'notes': 'updated', 'eat_dates': [str(cooking_event.cooking_date)]},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK

    def test_another_user_cannot_patch_event(
        self,
        auth_another_telegram_api_client: APIClient,
        cooking_event: CookingEvent,
    ) -> None:
        # queryset filters to owner, so 404 (not 403) is returned
        response = auth_another_telegram_api_client.patch(
            self.get_url(str(cooking_event.id)), data={'notes': 'hacked'}, format='json'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nonexistent_id_returns_404(self, auth_telegram_api_client: APIClient) -> None:
        response = auth_telegram_api_client.patch(self.get_url(str(uuid.uuid4())), data={'notes': 'x'}, format='json')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_notes_only_does_not_change_meal_plan_items(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_with_meal_plan_items: CookingEvent,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        event = cooking_event_with_meal_plan_items
        dates_before = set(MealPlanItem.objects.filter(cooking_event=event).values_list('date', flat=True))
        eat_dates = [str(d) for d in sorted(dates_before)]
        with django_assert_num_queries(8):
            auth_telegram_api_client.patch(
                self.get_url(str(event.id)), data={'notes': 'changed note', 'eat_dates': eat_dates}, format='json'
            )
        dates_after = set(MealPlanItem.objects.filter(cooking_event=event).values_list('date', flat=True))
        assert dates_before == dates_after

    def test_patch_cooking_date_only_does_not_shift_meal_plan_items(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_with_meal_plan_items: CookingEvent,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        event = cooking_event_with_meal_plan_items
        dates_before = set(MealPlanItem.objects.filter(cooking_event=event).values_list('date', flat=True))
        new_cooking_date = event.cooking_date - timedelta(days=1)
        eat_dates = [str(d) for d in sorted(dates_before)]
        with django_assert_num_queries(8):
            auth_telegram_api_client.patch(
                self.get_url(str(event.id)),
                data={'cooking_date': str(new_cooking_date), 'eat_dates': eat_dates},
                format='json',
            )
        dates_after = set(MealPlanItem.objects.filter(cooking_event=event).values_list('date', flat=True))
        assert dates_before == dates_after

    def test_changing_start_eating_date_shifts_meal_plan_item_dates(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_with_meal_plan_items: CookingEvent,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        event = cooking_event_with_meal_plan_items
        old_dates = sorted(MealPlanItem.objects.filter(cooking_event=event).values_list('date', flat=True))
        shift = timedelta(days=5)
        new_eat_dates = [str(d + shift) for d in old_dates]
        with django_assert_num_queries(11):
            auth_telegram_api_client.patch(
                self.get_url(str(event.id)),
                data={'eat_dates': new_eat_dates},
                format='json',
            )
        new_dates = sorted(MealPlanItem.objects.filter(cooking_event=event).values_list('date', flat=True))
        expected = [d + shift for d in old_dates]
        assert list(new_dates) == expected

    def test_increasing_duration_days_adds_new_meal_plan_items(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_with_meal_plan_items: CookingEvent,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        event = cooking_event_with_meal_plan_items
        old_dates = sorted(MealPlanItem.objects.filter(cooking_event=event).values_list('date', flat=True))
        extra_count = 2
        new_eat_dates = [str(d) for d in old_dates] + [
            str(old_dates[-1] + timedelta(days=i + 1)) for i in range(extra_count)
        ]
        with django_assert_num_queries(10):
            auth_telegram_api_client.patch(
                self.get_url(str(event.id)), data={'eat_dates': new_eat_dates}, format='json'
            )
        new_count = MealPlanItem.objects.filter(cooking_event=event).count()
        assert new_count == len(old_dates) + extra_count

    def test_decreasing_duration_days_removes_last_meal_plan_items(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_with_meal_plan_items: CookingEvent,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        event = cooking_event_with_meal_plan_items
        old_dates = sorted(MealPlanItem.objects.filter(cooking_event=event).values_list('date', flat=True))
        new_eat_dates = [str(d) for d in old_dates[:-1]]
        with django_assert_num_queries(9):
            auth_telegram_api_client.patch(
                self.get_url(str(event.id)), data={'eat_dates': new_eat_dates}, format='json'
            )
        new_count = MealPlanItem.objects.filter(cooking_event=event).count()
        assert new_count == len(old_dates) - 1
        remaining_dates = sorted(MealPlanItem.objects.filter(cooking_event=event).values_list('date', flat=True))
        # Last item (latest date) must have been removed
        assert remaining_dates == old_dates[:-1]

    def test_patch_event_without_meal_plan_items_creates_them(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event: CookingEvent,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        # cooking_event fixture does NOT create MealPlanItems (created directly, not via service)
        assert MealPlanItem.objects.filter(cooking_event=cooking_event).count() == 0
        eat_dates = [str(cooking_event.cooking_date + timedelta(days=i)) for i in range(3)]
        with django_assert_num_queries(10):
            auth_telegram_api_client.patch(
                self.get_url(str(cooking_event.id)),
                data={'notes': 'trigger update', 'eat_dates': eat_dates},
                format='json',
            )
        # updater creates MealPlanItems when none exist
        assert MealPlanItem.objects.filter(cooking_event=cooking_event).count() == 3

    def test_start_eating_date_before_cooking_date_returns_400(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event: CookingEvent,
    ) -> None:
        response = auth_telegram_api_client.patch(
            self.get_url(str(cooking_event.id)),
            data={'eat_dates': [str(cooking_event.cooking_date - timedelta(days=1))]},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_duration_days_zero_returns_400(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event: CookingEvent,
    ) -> None:
        response = auth_telegram_api_client.patch(
            self.get_url(str(cooking_event.id)), data={'eat_dates': []}, format='json'
        )
        assert response.status_code == status.HTTP_200_OK

    def test_duration_days_31_returns_400(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event: CookingEvent,
    ) -> None:
        eat_dates = [str(cooking_event.cooking_date + timedelta(days=i)) for i in range(31)]
        response = auth_telegram_api_client.patch(
            self.get_url(str(cooking_event.id)), data={'eat_dates': eat_dates}, format='json'
        )
        assert response.status_code == status.HTTP_200_OK

    def test_response_uses_read_serializer_with_nested_dish(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event: CookingEvent,
    ) -> None:
        response = auth_telegram_api_client.patch(
            self.get_url(str(cooking_event.id)),
            data={'notes': 'check serializer', 'eat_dates': [str(cooking_event.cooking_date)]},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data['dish'], dict)
        assert str(response.data['dish']['id']) == str(cooking_event.dish.id)

    def test_new_meal_plan_items_added_via_patch_inherit_cooking_event_color(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event: CookingEvent,
    ) -> None:
        # cooking_event fixture has no meal plan items; items created via patch must inherit event's color
        eat_dates = [str(cooking_event.cooking_date + timedelta(days=i)) for i in range(3)]
        auth_telegram_api_client.patch(
            self.get_url(str(cooking_event.id)),
            data={'eat_dates': eat_dates},
            format='json',
        )
        items = MealPlanItem.objects.filter(cooking_event=cooking_event)
        assert items.count() == 3
        assert all(item.color == cooking_event.color for item in items)

    def test_put_method_not_allowed(self, auth_telegram_api_client: APIClient, cooking_event: CookingEvent) -> None:
        response = auth_telegram_api_client.put(self.get_url(str(cooking_event.id)), data={}, format='json')
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestCookingEventViewSetDelete:
    def get_url(self, cooking_event_id: str) -> str:
        return reverse(
            'api_v1:planning:cooking:cooking-event-detail',
            kwargs={'cooking_event_id': cooking_event_id},
        )

    def test_anon_client_cannot_delete(self, api_client: APIClient, cooking_event: CookingEvent) -> None:
        response = api_client.delete(self.get_url(str(cooking_event.id)))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_owner_can_delete_own_event(self, auth_telegram_api_client: APIClient, cooking_event: CookingEvent) -> None:
        response = auth_telegram_api_client.delete(self.get_url(str(cooking_event.id)))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CookingEvent.objects.filter(pk=cooking_event.pk).exists()

    def test_another_user_cannot_delete_event(
        self,
        auth_another_telegram_api_client: APIClient,
        cooking_event: CookingEvent,
    ) -> None:
        # queryset filters to owner, so 404 (not 403) is returned
        response = auth_another_telegram_api_client.delete(self.get_url(str(cooking_event.id)))
        assert response.status_code == status.HTTP_404_NOT_FOUND
        # Event must still exist
        assert CookingEvent.objects.filter(pk=cooking_event.pk).exists()

    def test_nonexistent_id_returns_404(self, auth_telegram_api_client: APIClient) -> None:
        response = auth_telegram_api_client.delete(self.get_url(str(uuid.uuid4())))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_deleting_event_cascades_to_meal_plan_items(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event_with_meal_plan_items: CookingEvent,
    ) -> None:
        event = cooking_event_with_meal_plan_items
        assert MealPlanItem.objects.filter(cooking_event=event).count() == 5
        auth_telegram_api_client.delete(self.get_url(str(event.id)))
        assert not MealPlanItem.objects.filter(cooking_event=event).exists()


class TestCookingEventViewSetQueryCount:
    list_url = reverse('api_v1:planning:cooking:cooking-event-list')

    def get_detail_url(self, cooking_event_id: str) -> str:
        return reverse(
            'api_v1:planning:cooking:cooking-event-detail',
            kwargs={'cooking_event_id': cooking_event_id},
        )

    @pytest.mark.usefixtures('multiple_cooking_events')
    def test_list_makes_exactly_4_queries(
        self, auth_telegram_api_client: APIClient, django_assert_num_queries: DjangoAssertNumQueries
    ) -> None:
        with django_assert_num_queries(4):
            response = auth_telegram_api_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 5

    @pytest.mark.usefixtures('multiple_cooking_events')
    def test_list_query_count_does_not_grow_with_more_events(
        self,
        auth_telegram_api_client: APIClient,
        telegram_user: User,
        dish_global: Dish,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        extra = [
            CookingEvent(
                owner=telegram_user,
                dish=dish_global,
                cooking_date=WEEK_START + timedelta(days=500 + i * 10),
            )
            for i in range(5)
        ]
        CookingEvent.objects.bulk_create(extra)
        with django_assert_num_queries(4):
            response = auth_telegram_api_client.get(self.list_url)
        assert response.data['count'] == 10

    def test_retrieve_makes_exactly_4_query(
        self,
        auth_telegram_api_client: APIClient,
        cooking_event: CookingEvent,
        django_assert_num_queries: DjangoAssertNumQueries,
    ) -> None:
        with django_assert_num_queries(4):
            response = auth_telegram_api_client.get(self.get_detail_url(str(cooking_event.id)))
        assert response.status_code == status.HTTP_200_OK
