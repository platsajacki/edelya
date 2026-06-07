from pytest_mock import MockType

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.dishes.api.serializers.ai_drafts import DishAIDraftSerializer
from apps.dishes.models import DishAIDraft
from apps.dishes.models.model_enums import DishAIDraftStatus
from apps.subscriptions.models import Subscription
from apps.users.models import User


class TestDishAIDraftViewSetList:
    list_url = reverse('api_v1:dishes:dishes:dish-ai-draft-list')

    def test_anon_client_cannot_get_draft_list(self, api_client: APIClient) -> None:
        response = api_client.get(self.list_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_client_can_get_own_draft_list(
        self,
        auth_telegram_api_client: APIClient,
        dish_ai_draft: DishAIDraft,
        another_user_dish_ai_draft: DishAIDraft,
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'] == DishAIDraftSerializer([dish_ai_draft], many=True).data

    def test_authenticated_client_can_filter_draft_list_by_status(
        self,
        auth_telegram_api_client: APIClient,
        dish_ai_draft: DishAIDraft,
        parsed_dish_ai_draft: DishAIDraft,
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url, data={'status': DishAIDraftStatus.PARSED})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'] == DishAIDraftSerializer([parsed_dish_ai_draft], many=True).data

    def test_authenticated_client_can_filter_draft_list_by_source_text(
        self,
        auth_telegram_api_client: APIClient,
        dish_ai_draft: DishAIDraft,
        parsed_dish_ai_draft: DishAIDraft,
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url, data={'source_text__icontains': 'parsed'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'] == DishAIDraftSerializer([parsed_dish_ai_draft], many=True).data


class TestDishAIDraftViewSetRetrieve:
    def get_detail_url(self, id: str) -> str:
        return reverse('api_v1:dishes:dishes:dish-ai-draft-detail', kwargs={'draft_id': id})

    def test_anon_client_cannot_get_draft_detail(self, api_client: APIClient, dish_ai_draft: DishAIDraft) -> None:
        response = api_client.get(self.get_detail_url(str(dish_ai_draft.id)))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_client_can_get_own_draft_detail(
        self, auth_telegram_api_client: APIClient, dish_ai_draft: DishAIDraft
    ) -> None:
        response = auth_telegram_api_client.get(self.get_detail_url(str(dish_ai_draft.id)))
        assert response.status_code == status.HTTP_200_OK
        assert response.data == DishAIDraftSerializer(dish_ai_draft).data

    def test_authenticated_client_cannot_get_another_user_draft_detail(
        self, auth_telegram_api_client: APIClient, another_user_dish_ai_draft: DishAIDraft
    ) -> None:
        response = auth_telegram_api_client.get(self.get_detail_url(str(another_user_dish_ai_draft.id)))
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDishAIDraftViewSetCreate:
    list_url = reverse('api_v1:dishes:dishes:dish-ai-draft-list')

    def test_anon_client_cannot_create_draft(self, api_client: APIClient) -> None:
        response = api_client.post(self.list_url, data={'source_text': 'Recipe source text'})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_client_without_ai_recipes_cannot_create_draft(
        self, auth_telegram_api_client: APIClient
    ) -> None:
        response = auth_telegram_api_client.post(self.list_url, data={'source_text': 'Recipe source text'})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_authenticated_client_can_create_draft(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        mock_process_ai_draft_delay: MockType,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        with TestCase.captureOnCommitCallbacks(execute=True):
            response = api_client.post(self.list_url, data={'source_text': 'Recipe source text'})
        assert response.status_code == status.HTTP_201_CREATED
        draft = DishAIDraft.objects.get(id=response.data['id'])
        assert draft.owner == telegram_user
        assert draft.source_text == 'Recipe source text'
        assert draft.status == DishAIDraftStatus.PROCESSING
        mock_process_ai_draft_delay.assert_called_once_with(str(draft.id))

    def test_authenticated_client_cannot_create_draft_with_short_source_text(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        mock_process_ai_draft_delay: MockType,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(self.list_url, data={'source_text': 'short'})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        mock_process_ai_draft_delay.assert_not_called()

    def test_authenticated_client_cannot_create_draft_when_period_limit_exceeded(
        self,
        api_client: APIClient,
        telegram_user: User,
        active_subscription_with_period: Subscription,
        dish_ai_draft_limit: list[DishAIDraft],
        mock_process_ai_draft_delay: MockType,
    ) -> None:
        api_client.force_authenticate(user=telegram_user)
        response = api_client.post(self.list_url, data={'source_text': 'Recipe source text'})
        assert active_subscription_with_period.ended_at is not None
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {
            'detail': 'AI recipe limit for the current subscription period has been exceeded.',
            'code': 'ai_recipe_limit_exceeded',
            'reset_at': active_subscription_with_period.ended_at.isoformat(),
        }
        mock_process_ai_draft_delay.assert_not_called()
