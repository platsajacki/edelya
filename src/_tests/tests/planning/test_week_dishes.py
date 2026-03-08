import pytest

from datetime import date, timedelta

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.dishes.models import Dish
from apps.planning.api.serializers.cooking import CookingEventSerializer
from apps.planning.api.serializers.meal_plan import MealPlanItemSerializer
from apps.planning.models import CookingEvent, MealPlanItem
from apps.users.models import User


class TestWeekDishesAPIView:
    def get_url(self, year: int, week: int) -> str:
        return reverse('api_v1:planning:week-dishes', kwargs={'year': year, 'week': week})

    def test_anon_client_cannot_get_week_dishes(self, api_client: APIClient, week_year: int, week_number: int) -> None:
        response = api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_client_gets_empty_lists_for_empty_week(
        self, auth_telegram_api_client: APIClient, week_year: int, week_number: int
    ) -> None:
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['meal_plan_items'] == []
        assert response.data['cooking_events'] == []

    def test_response_contains_start_and_end_week_dates(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
        week_start: date,
        week_end: date,
    ) -> None:
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['start_week'] == str(week_start)
        assert response.data['end_week'] == str(week_end)

    def test_start_week_is_monday_end_week_is_sunday(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
        week_start: date,
        week_end: date,
    ) -> None:
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        start = date.fromisoformat(response.data['start_week'])
        end = date.fromisoformat(response.data['end_week'])
        assert start == week_start
        assert end == week_end
        assert start.weekday() == 0  # Monday
        assert end.weekday() == 6  # Sunday
        assert end - start == timedelta(days=6)

    def test_returns_own_meal_plan_item(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
        meal_plan_item: MealPlanItem,
    ) -> None:
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['meal_plan_items']) == 1
        assert str(response.data['meal_plan_items'][0]['id']) == str(meal_plan_item.id)

    def test_meal_plan_item_serialization(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
        meal_plan_item: MealPlanItem,
    ) -> None:
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        item = response.data['meal_plan_items'][0]
        assert str(item['id']) == str(meal_plan_item.id)
        assert item['date'] == str(meal_plan_item.date)
        assert item['position'] == meal_plan_item.position
        assert item['is_manual'] == meal_plan_item.is_manual
        assert item['dish']['id'] == str(meal_plan_item.dish.id)

    def test_meal_plan_item_matches_serializer_output(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
        meal_plan_item: MealPlanItem,
    ) -> None:
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        item = MealPlanItem.objects.select_related('dish', 'dish__category').get(pk=meal_plan_item.pk)
        expected = MealPlanItemSerializer(item).data
        assert response.data['meal_plan_items'][0] == expected

    def test_returns_own_cooking_event(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
        cooking_event: CookingEvent,
    ) -> None:
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['cooking_events']) == 1
        assert str(response.data['cooking_events'][0]['id']) == str(cooking_event.id)

    def test_cooking_event_serialization(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
        cooking_event: CookingEvent,
    ) -> None:
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        event = response.data['cooking_events'][0]
        assert str(event['id']) == str(cooking_event.id)
        assert event['cooking_date'] == str(cooking_event.cooking_date)
        assert event['duration_days'] == cooking_event.duration_days
        assert event['dish']['id'] == str(cooking_event.dish.id)

    def test_cooking_event_matches_serializer_output(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
        cooking_event: CookingEvent,
    ) -> None:
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        event = CookingEvent.objects.select_related('dish', 'dish__category').get(pk=cooking_event.pk)
        expected = CookingEventSerializer(event).data
        assert response.data['cooking_events'][0] == expected

    def test_returns_both_meal_plan_items_and_cooking_events(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
        meal_plan_item: MealPlanItem,
        cooking_event: CookingEvent,
    ) -> None:
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['meal_plan_items']) == 1
        assert len(response.data['cooking_events']) == 1
        assert str(response.data['meal_plan_items'][0]['id']) == str(meal_plan_item.id)
        assert str(response.data['cooking_events'][0]['id']) == str(cooking_event.id)

    @pytest.mark.usefixtures('another_user_meal_plan_item')
    def test_does_not_return_another_users_meal_plan_item(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
    ) -> None:
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['meal_plan_items'] == []

    @pytest.mark.usefixtures('another_user_meal_plan_item')
    def test_does_not_return_another_users_cooking_event(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
    ) -> None:
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['cooking_events'] == []

    def test_meal_plan_item_on_week_start_is_included(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
        week_start: date,
        telegram_user: User,
        dish_global: Dish,
    ) -> None:
        MealPlanItem.objects.create(owner=telegram_user, dish=dish_global, date=week_start, position=10, is_manual=True)
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['meal_plan_items']) == 1

    def test_meal_plan_item_on_week_end_is_included(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
        week_end: date,
        telegram_user: User,
        dish_global: Dish,
    ) -> None:
        MealPlanItem.objects.create(owner=telegram_user, dish=dish_global, date=week_end, position=10, is_manual=True)
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['meal_plan_items']) == 1

    def test_meal_plan_item_before_week_start_is_excluded(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
        week_start: date,
        telegram_user: User,
        dish_global: Dish,
    ) -> None:
        MealPlanItem.objects.create(
            owner=telegram_user, dish=dish_global, date=week_start - timedelta(days=1), position=10, is_manual=True
        )
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['meal_plan_items'] == []

    def test_meal_plan_item_after_week_end_is_excluded(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
        week_end: date,
        telegram_user: User,
        dish_global: Dish,
    ) -> None:
        MealPlanItem.objects.create(
            owner=telegram_user, dish=dish_global, date=week_end + timedelta(days=1), position=10, is_manual=True
        )
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['meal_plan_items'] == []

    def test_cooking_event_on_week_start_is_included(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
        week_start: date,
        telegram_user: User,
        dish_global: Dish,
    ) -> None:
        CookingEvent.objects.create(
            owner=telegram_user,
            dish=dish_global,
            cooking_date=week_start,
            duration_days=1,
            start_eating_date=week_start,
        )
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['cooking_events']) == 1

    def test_cooking_event_on_week_end_is_included(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
        week_end: date,
        telegram_user: User,
        dish_global: Dish,
    ) -> None:
        CookingEvent.objects.create(
            owner=telegram_user, dish=dish_global, cooking_date=week_end, duration_days=1, start_eating_date=week_end
        )
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['cooking_events']) == 1

    def test_cooking_event_before_week_start_is_excluded(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
        week_start: date,
        telegram_user: User,
        dish_global: Dish,
    ) -> None:
        before = week_start - timedelta(days=1)
        CookingEvent.objects.create(
            owner=telegram_user, dish=dish_global, cooking_date=before, duration_days=1, start_eating_date=before
        )
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['cooking_events'] == []

    def test_cooking_event_after_week_end_is_excluded(
        self,
        auth_telegram_api_client: APIClient,
        week_year: int,
        week_number: int,
        week_end: date,
        telegram_user: User,
        dish_global: Dish,
    ) -> None:
        after = week_end + timedelta(days=1)
        CookingEvent.objects.create(
            owner=telegram_user, dish=dish_global, cooking_date=after, duration_days=1, start_eating_date=after
        )
        response = auth_telegram_api_client.get(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['cooking_events'] == []

    def test_week_zero_returns_400(self, auth_telegram_api_client: APIClient, week_year: int) -> None:
        response = auth_telegram_api_client.get(self.get_url(week_year, 0))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_week_54_returns_400(self, auth_telegram_api_client: APIClient) -> None:
        # 2025 has only 52 ISO weeks, so week 54 is always invalid
        response = auth_telegram_api_client.get(self.get_url(2025, 54))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_week_53_for_non_long_year_returns_400(self, auth_telegram_api_client: APIClient) -> None:
        # 2025 has only 52 ISO weeks, so week 53 is invalid
        response = auth_telegram_api_client.get(self.get_url(2025, 53))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_week_53_for_long_year_returns_200(self, auth_telegram_api_client: APIClient) -> None:
        # 2026 has 53 ISO weeks
        response = auth_telegram_api_client.get(self.get_url(2026, 53))
        assert response.status_code == status.HTTP_200_OK

    def test_week_52_returns_200(self, auth_telegram_api_client: APIClient, week_year: int) -> None:
        response = auth_telegram_api_client.get(self.get_url(week_year, 52))
        assert response.status_code == status.HTTP_200_OK

    def test_week_1_returns_200(self, auth_telegram_api_client: APIClient, week_year: int) -> None:
        response = auth_telegram_api_client.get(self.get_url(week_year, 1))
        assert response.status_code == status.HTTP_200_OK

    def test_post_method_not_allowed(
        self, auth_telegram_api_client: APIClient, week_year: int, week_number: int
    ) -> None:
        response = auth_telegram_api_client.post(self.get_url(week_year, week_number), data={}, format='json')
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_put_method_not_allowed(
        self, auth_telegram_api_client: APIClient, week_year: int, week_number: int
    ) -> None:
        response = auth_telegram_api_client.put(self.get_url(week_year, week_number), data={}, format='json')
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_patch_method_not_allowed(
        self, auth_telegram_api_client: APIClient, week_year: int, week_number: int
    ) -> None:
        response = auth_telegram_api_client.patch(self.get_url(week_year, week_number), data={}, format='json')
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_method_not_allowed(
        self, auth_telegram_api_client: APIClient, week_year: int, week_number: int
    ) -> None:
        response = auth_telegram_api_client.delete(self.get_url(week_year, week_number))
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
