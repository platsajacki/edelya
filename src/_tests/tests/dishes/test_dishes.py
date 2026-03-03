import pytest

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.dishes.api.serializers.dishes import DishCategorySerializer
from apps.dishes.models import DishCategory


class TestDishCategoryViewSet:
    list_url = reverse('api_v1:dishes:dishes:dish-category-list')

    def get_detail_url(self, id: str) -> str:
        return reverse('api_v1:dishes:dishes:dish-category-detail', kwargs={'dish_category_id': id})

    def test_anon_client_cannot_get_dish_category_list(self, api_client: APIClient) -> None:
        response = api_client.get(self.list_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_client_can_get_dish_category_list(
        self, auth_telegram_api_client: APIClient, dish_category: DishCategory
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        results = response.data['results']
        assert results == DishCategorySerializer([dish_category], many=True).data

    def test_authenticated_client_can_filter_dish_category_list_by_name(
        self, auth_telegram_api_client: APIClient, dish_category: DishCategory
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url, data={'name': dish_category.name})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        results = response.data['results']
        assert results == DishCategorySerializer([dish_category], many=True).data

    def test_authenticated_client_get_dish_category_list_with_nonexistent_name_filter(
        self, auth_telegram_api_client: APIClient
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url, data={'name': 'nonexistent'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []

    @pytest.mark.usefixtures('dish_categories')
    def test_authenticated_client_get_dish_category_list_with_ordering(
        self, auth_telegram_api_client: APIClient, dish_category_data: list[dict]
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url, data={'ordering': '-name'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 5
        results = response.data['results']
        expected_names = sorted([data['name'] for data in dish_category_data[5::]], reverse=True)
        assert [result['name'] for result in results] == expected_names

    def test_anon_client_cannot_get_dish_category_detail(
        self, api_client: APIClient, dish_category: DishCategory
    ) -> None:
        url = self.get_detail_url(str(dish_category.id))
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_client_can_get_dish_category_detail(
        self, auth_telegram_api_client: APIClient, dish_category: DishCategory
    ) -> None:
        url = self.get_detail_url(str(dish_category.id))
        response = auth_telegram_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == DishCategorySerializer(dish_category).data
