import pytest

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.dishes.api.serializers.ingredients import IngredientCategorySerializer, IngredientSerializer
from apps.dishes.models import IngredientCategory
from apps.dishes.models.ingredients import Ingredient
from apps.dishes.models.model_enums import Unit
from apps.users.models import User


class TestIngredientCategoryViewSet:
    list_url = reverse('api_v1:dishes:ingredients:ingredient-category-list')

    def get_detail_url(self, id: str) -> str:
        return reverse('api_v1:dishes:ingredients:ingredient-category-detail', kwargs={'ingredient_category_id': id})

    def test_anon_clien_cannot_get_ingredient_category_list(self, api_client: APIClient) -> None:
        response = api_client.get(self.list_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_client_can_get_ingredient_category_list(
        self, auth_telegram_api_client: APIClient, ingredient_category: IngredientCategory
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        results = response.data['results']
        assert results == IngredientCategorySerializer([ingredient_category], many=True).data

    @pytest.mark.usefixtures('ingredient_categories')
    def test_authenticated_client_can_filter_ingredient_category_list_by_name(
        self, auth_telegram_api_client: APIClient, ingredient_category: IngredientCategory
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url, data={'name': ingredient_category.name})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        results = response.data['results']
        assert results == IngredientCategorySerializer([ingredient_category], many=True).data

    @pytest.mark.usefixtures('ingredient_categories')
    def test_authenticated_client_get_ingredient_category_list_with_nonexistent_name_filter(
        self, auth_telegram_api_client: APIClient
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url, data={'name': 'nonexistent'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []

    @pytest.mark.usefixtures('ingredient_categories')
    def test_authenticated_client_get_ingredient_category_list_with_ordering(
        self, auth_telegram_api_client: APIClient, ingredient_category_data: list[dict]
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url, data={'ordering': '-name'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 5
        results = response.data['results']
        expected_names = sorted([data['name'] for data in ingredient_category_data[5::]], reverse=True)
        assert [result['name'] for result in results] == expected_names

    def test_anon_client_cannot_get_ingredient_category_detail(
        self, api_client: APIClient, ingredient_category: IngredientCategory
    ) -> None:
        url = self.get_detail_url(str(ingredient_category.id))
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_client_can_get_ingredient_category_detail(
        self, auth_telegram_api_client: APIClient, ingredient_category: IngredientCategory
    ) -> None:
        url = self.get_detail_url(str(ingredient_category.id))
        response = auth_telegram_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == IngredientCategorySerializer(ingredient_category).data


class TestIngredientViewSet:
    list_url = reverse('api_v1:dishes:ingredients:ingredient-list')

    def get_detail_url(self, id: str) -> str:
        return reverse('api_v1:dishes:ingredients:ingredient-detail', kwargs={'ingredient_id': id})

    def test_anon_client_cannot_get_ingredient_list(self, api_client: APIClient) -> None:
        response = api_client.get(self.list_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_client_can_get_ingredient_list(
        self, auth_telegram_api_client: APIClient, ingredient_global: Ingredient
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        results = response.data['results']
        assert results == IngredientSerializer([ingredient_global], many=True).data

    @pytest.mark.usefixtures('ingredients')
    def test_authenticated_client_can_filter_ingredient_list_by_name(
        self, auth_telegram_api_client: APIClient, ingredient_user: Ingredient
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url, data={'name': ingredient_user.name})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        results = response.data['results']
        assert results == IngredientSerializer([ingredient_user], many=True).data

    def test_authenticated_client_cannot_get_another_user_ingredients(
        self, auth_telegram_api_client: APIClient, ingredient_global: Ingredient, another_telegram_user: User
    ) -> None:
        ingredient_global.owner = another_telegram_user
        ingredient_global.save(update_fields=['owner'])
        response = auth_telegram_api_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []

    @pytest.mark.usefixtures('ingredients')
    def test_authenticated_client_get_ingredient_list_filtered_by_category(
        self, auth_telegram_api_client: APIClient, second_ingredient_category: IngredientCategory
    ) -> None:
        ingredient = Ingredient.objects.first()
        assert ingredient is not None
        ingredient.category = second_ingredient_category
        ingredient.save(update_fields=['category'])
        response = auth_telegram_api_client.get(self.list_url, data={'category': str(second_ingredient_category.id)})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        results = response.data['results']
        assert results == IngredientSerializer([ingredient], many=True).data

    def test_list_returns_global_and_owner_ingredients_only(
        self,
        auth_telegram_api_client: APIClient,
        ingredient_global: Ingredient,
        ingredient_user: Ingredient,
        another_telegram_user: User,
    ) -> None:
        other = Ingredient.objects.create(
            name='other',
            base_unit=Unit.GRAM,
            category=ingredient_global.category,
            owner=another_telegram_user,
        )
        response = auth_telegram_api_client.get(self.list_url)
        returned_ids = {item['id'] for item in response.data['results']}
        assert str(ingredient_global.id) in returned_ids
        assert str(ingredient_user.id) in returned_ids
        assert str(other.id) not in returned_ids

    def test_filtering_by_category_and_base_unit(
        self, auth_telegram_api_client: APIClient, ingredient_category: IngredientCategory, telegram_user: User
    ) -> None:
        Ingredient.objects.filter(owner=telegram_user).delete()
        Ingredient.objects.create(
            name='aaa',
            base_unit=Unit.GRAM,
            category=ingredient_category,
            owner=telegram_user,
        )
        Ingredient.objects.create(
            name='zzz',
            base_unit=Unit.PIECE,
            category=ingredient_category,
            owner=telegram_user,
        )
        Ingredient.objects.create(
            name='bbb',
            base_unit=Unit.GRAM,
            category=ingredient_category,
            owner=telegram_user,
        )
        response = auth_telegram_api_client.get(
            self.list_url,
            data={'category': str(ingredient_category.id), 'base_unit': Unit.GRAM},
        )
        assert response.status_code == status.HTTP_200_OK
        assert [item['name'] for item in response.data['results']] == ['aaa', 'bbb']

    def test_authenticated_client_can_update_own_ingredient(
        self, auth_telegram_api_client: APIClient, ingredient_user: Ingredient
    ) -> None:
        url = self.get_detail_url(str(ingredient_user.id))
        response = auth_telegram_api_client.patch(
            url,
            data={'name': 'Updated', 'base_unit': Unit.LITER},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        ingredient_user.refresh_from_db()
        assert ingredient_user.name == 'Updated'
        assert ingredient_user.base_unit == Unit.LITER

    def test_authenticated_client_cannot_update_foreign_ingredient(
        self,
        auth_telegram_api_client: APIClient,
        another_telegram_user: User,
        second_ingredient_category: IngredientCategory,
    ) -> None:
        foreign = Ingredient.objects.create(
            name='foreign',
            base_unit=Unit.CUP,
            category=second_ingredient_category,
            owner=another_telegram_user,
        )
        response = auth_telegram_api_client.patch(
            self.get_detail_url(str(foreign.id)),
            data={'name': 'nope'},
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_authenticated_client_can_delete_own_ingredient(
        self, auth_telegram_api_client: APIClient, ingredient_user: Ingredient
    ) -> None:
        url = self.get_detail_url(str(ingredient_user.id))
        response = auth_telegram_api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        ingredient_user.refresh_from_db()
        assert not ingredient_user.is_active
        assert auth_telegram_api_client.get(url).status_code == status.HTTP_404_NOT_FOUND

    def test_authenticated_client_cannot_delete_foreign_ingredient(
        self,
        auth_telegram_api_client: APIClient,
        another_telegram_user: User,
        second_ingredient_category: IngredientCategory,
    ) -> None:
        foreign = Ingredient.objects.create(
            name='foreign',
            base_unit=Unit.CUP,
            category=second_ingredient_category,
            owner=another_telegram_user,
        )
        response = auth_telegram_api_client.delete(self.get_detail_url(str(foreign.id)))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_authenticated_client_cannot_make_duplicate_ingredient(
        self, auth_telegram_api_client: APIClient, ingredient_user: Ingredient, ingredient_category: IngredientCategory
    ) -> None:
        response = auth_telegram_api_client.post(
            self.list_url,
            data={
                'name': ingredient_user.name,
                'base_unit': ingredient_user.base_unit,
                'category': str(ingredient_user.category.id),
            },
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'An ingredient with this name already exists for this user' in str(response.data)

    def test_authenticated_client_can_create_ingredient(
        self, auth_telegram_api_client: APIClient, ingredient_category: IngredientCategory
    ) -> None:
        response = auth_telegram_api_client.post(
            self.list_url,
            data={
                'name': 'New Ingredient',
                'base_unit': Unit.TABLESPOON,
                'category': str(ingredient_category.id),
            },
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Ingredient'
        assert response.data['base_unit'] == Unit.TABLESPOON
        assert response.data['category']['id'] == str(ingredient_category.id)
