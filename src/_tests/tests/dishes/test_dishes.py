import pytest

import uuid
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.dishes.api.serializers.dishes import DishCategorySerializer, DishReadSerializer
from apps.dishes.models import Dish, DishCategory, DishIngredient
from apps.dishes.models.ingredients import Ingredient
from apps.users.models import User


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


class TestDishViewSet:
    list_url = reverse('api_v1:dishes:dishes:dish-list')

    def get_detail_url(self, id: str) -> str:
        return reverse('api_v1:dishes:dishes:dish-detail', kwargs={'dish_id': id})

    def test_anon_client_cannot_get_dish_list(self, api_client: APIClient) -> None:
        response = api_client.get(self.list_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_client_can_get_dish_list(
        self, auth_telegram_api_client: APIClient, dish_global: Dish
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        results = response.data['results']
        assert results == DishReadSerializer([dish_global], many=True).data

    def test_authenticated_client_cannot_see_another_users_dishes(
        self, auth_telegram_api_client: APIClient, dish_global: Dish, another_telegram_user: User
    ) -> None:
        dish_global.owner = another_telegram_user
        dish_global.save(update_fields=['owner'])
        response = auth_telegram_api_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []

    def test_owened_first_puts_global_dishes_last(
        self,
        auth_telegram_api_client: APIClient,
        dish_global: Dish,
        dish_user: Dish,
        another_telegram_user: User,
        dish_category: DishCategory,
    ) -> None:
        # create a foreign-owned dish so we have: user-owned, foreign-owned, and global (owner=None)
        Dish.objects.create(name=dish_user.name, category=dish_category, owner=another_telegram_user)
        response = auth_telegram_api_client.get(self.list_url, data={'owened_first': 'true'})
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        # the global dish (owner=None) must be last because filter orders owner_id with nulls_last=True
        assert results[0]['id'] == str(dish_user.id)

    def test_list_returns_global_and_owner_dishes_only(
        self,
        auth_telegram_api_client: APIClient,
        dish_global: Dish,
        dish_user: Dish,
        another_telegram_user: User,
        dish_category: DishCategory,
    ) -> None:
        other = Dish.objects.create(
            name='unique other dish xyz',
            category=dish_category,
            owner=another_telegram_user,
        )
        response = auth_telegram_api_client.get(self.list_url)
        returned_ids = {item['id'] for item in response.data['results']}
        assert str(dish_global.id) in returned_ids
        assert str(dish_user.id) in returned_ids
        assert str(other.id) not in returned_ids

    @pytest.mark.usefixtures('dishes')
    def test_authenticated_client_can_filter_dish_list_by_name(
        self, auth_telegram_api_client: APIClient, dish_global: Dish
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url, data={'name': dish_global.name})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['name'] == dish_global.name

    def test_authenticated_client_can_filter_dish_list_by_category(
        self,
        auth_telegram_api_client: APIClient,
        dish_global: Dish,
        second_dish_category: DishCategory,
    ) -> None:
        Dish.objects.create(name='category filter dish', category=second_dish_category)
        response = auth_telegram_api_client.get(self.list_url, data={'category': str(second_dish_category.id)})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['category']['id'] == str(second_dish_category.id)

    def test_anon_client_cannot_get_dish_detail(self, api_client: APIClient, dish_user: Dish) -> None:
        url = self.get_detail_url(str(dish_user.id))
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_client_can_get_dish_detail(
        self, auth_telegram_api_client: APIClient, dish_user: Dish
    ) -> None:
        url = self.get_detail_url(str(dish_user.id))
        response = auth_telegram_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert dish_user.owner is not None
        assert response.data == DishReadSerializer(Dish.objects.for_user(dish_user.owner).get(id=dish_user.id)).data

    def test_authenticated_client_can_get_global_dish_detail(
        self, auth_telegram_api_client: APIClient, dish_global: Dish
    ) -> None:
        url = self.get_detail_url(str(dish_global.id))
        response = auth_telegram_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(dish_global.id)

    def test_authenticated_client_cannot_get_another_users_dish_detail(
        self, auth_telegram_api_client: APIClient, dish_user: Dish, another_telegram_user: User
    ) -> None:
        dish_user.owner = another_telegram_user
        dish_user.save(update_fields=['owner'])
        url = self.get_detail_url(str(dish_user.id))
        response = auth_telegram_api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_authenticated_client_can_create_dish(
        self,
        auth_telegram_api_client: APIClient,
        dish_category: DishCategory,
        ingredient_global: Ingredient,
        telegram_user: User,
    ) -> None:
        response = auth_telegram_api_client.post(
            self.list_url,
            data={
                'category': str(dish_category.id),
                'name': 'Brand New Dish',
                'dish_ingredients': [
                    {'ingredient': str(ingredient_global.id), 'amount': '150.000', 'is_optional': False}
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Brand New Dish'
        assert response.data['category']['id'] == str(dish_category.id)
        assert len(response.data['dish_ingredients']) == 1
        assert response.data['dish_ingredients'][0]['ingredient']['id'] == str(ingredient_global.id)
        assert Dish.objects.filter(name='Brand New Dish', owner=telegram_user).exists()

    def test_authenticated_client_cannot_create_dish_without_ingredients(
        self, auth_telegram_api_client: APIClient, dish_category: DishCategory
    ) -> None:
        response = auth_telegram_api_client.post(
            self.list_url,
            data={
                'category': str(dish_category.id),
                'name': 'No Ingredient Dish',
                'dish_ingredients': [],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not Dish.objects.filter(name='No Ingredient Dish').exists()

    def test_only_owned_filters_out_global_and_foreign(
        self,
        auth_telegram_api_client: APIClient,
        dish_global: Dish,
        dish_user: Dish,
        another_telegram_user: User,
        dish_category: DishCategory,
    ) -> None:
        # ensure there's a foreign-owned dish present in DB
        foreign = Dish.objects.create(name='foreign owned dish 2', category=dish_category, owner=another_telegram_user)
        response = auth_telegram_api_client.get(self.list_url, data={'only_owned': 'true'})
        assert response.status_code == status.HTTP_200_OK
        ids = {item['id'] for item in response.data['results']}
        assert str(dish_user.id) in ids
        assert str(dish_global.id) not in ids
        assert str(foreign.id) not in ids

    def test_only_global_returns_only_global_dishes(
        self,
        auth_telegram_api_client: APIClient,
        dish_global: Dish,
        dish_user: Dish,
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url, data={'only_global': 'true'})
        assert response.status_code == status.HTTP_200_OK
        ids = {item['id'] for item in response.data['results']}
        assert str(dish_global.id) in ids
        assert str(dish_user.id) not in ids

    def test_authenticated_client_cannot_create_dish_with_duplicate_name(
        self,
        auth_telegram_api_client: APIClient,
        dish_user: Dish,
        ingredient_global: Ingredient,
    ) -> None:
        response = auth_telegram_api_client.post(
            self.list_url,
            data={
                'category': str(dish_user.category.id),
                'name': dish_user.name,
                'dish_ingredients': [
                    {'ingredient': str(ingredient_global.id), 'amount': '100.000', 'is_optional': False}
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_authenticated_client_cannot_create_dish_with_nonexistent_ingredient(
        self, auth_telegram_api_client: APIClient, dish_category: DishCategory
    ) -> None:
        response = auth_telegram_api_client.post(
            self.list_url,
            data={
                'category': str(dish_category.id),
                'name': 'Dish With Bad Ingredient',
                'dish_ingredients': [{'ingredient': str(uuid.uuid4()), 'amount': '100.000', 'is_optional': False}],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert not Dish.objects.filter(name='Dish With Bad Ingredient').exists()

    def test_authenticated_client_cannot_create_dish_with_duplicate_ingredients(
        self,
        auth_telegram_api_client: APIClient,
        dish_category: DishCategory,
        ingredient_global: Ingredient,
    ) -> None:
        response = auth_telegram_api_client.post(
            self.list_url,
            data={
                'category': str(dish_category.id),
                'name': 'Dish With Dup Ingredients',
                'dish_ingredients': [
                    {'ingredient': str(ingredient_global.id), 'amount': '100.000', 'is_optional': False},
                    {'ingredient': str(ingredient_global.id), 'amount': '50.000', 'is_optional': True},
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not Dish.objects.filter(name='Dish With Dup Ingredients').exists()

    def test_authenticated_client_can_create_dish_with_own_ingredient(
        self,
        auth_telegram_api_client: APIClient,
        dish_category: DishCategory,
        ingredient_user: Ingredient,
        telegram_user: User,
    ) -> None:
        response = auth_telegram_api_client.post(
            self.list_url,
            data={
                'category': str(dish_category.id),
                'name': 'Dish With Own Ingredient',
                'dish_ingredients': [{'ingredient': str(ingredient_user.id), 'amount': '75.000', 'is_optional': False}],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Dish With Own Ingredient'
        assert Dish.objects.filter(name='Dish With Own Ingredient', owner=telegram_user).exists()

    def test_anon_client_cannot_create_dish(
        self, api_client: APIClient, dish_category: DishCategory, ingredient_global: Ingredient
    ) -> None:
        response = api_client.post(
            self.list_url,
            data={
                'category': str(dish_category.id),
                'name': 'Anon Dish',
                'dish_ingredients': [
                    {'ingredient': str(ingredient_global.id), 'amount': '100.000', 'is_optional': False}
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert not Dish.objects.filter(name='Anon Dish').exists()

    def test_authenticated_client_cannot_create_dish_with_another_users_ingredient(
        self,
        auth_telegram_api_client: APIClient,
        dish_category: DishCategory,
        ingredient_data: list[dict],
        another_telegram_user: User,
    ) -> None:
        from apps.dishes.models.ingredients import Ingredient as _Ingredient

        foreign_ingredient = _Ingredient.objects.create(**{**ingredient_data[2], 'owner': another_telegram_user})
        response = auth_telegram_api_client.post(
            self.list_url,
            data={
                'category': str(dish_category.id),
                'name': 'Dish With Foreign Ingredient',
                'dish_ingredients': [
                    {'ingredient': str(foreign_ingredient.id), 'amount': '100.000', 'is_optional': False}
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert not Dish.objects.filter(name='Dish With Foreign Ingredient').exists()

    # -- PUT / update --

    def test_anon_client_cannot_put_dish(self, api_client: APIClient, dish_user: Dish) -> None:
        url = self.get_detail_url(str(dish_user.id))
        response = api_client.put(url, data={}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_client_can_put_own_dish_fields(
        self,
        auth_telegram_api_client: APIClient,
        dish_user_with_ingredient: Dish,
        ingredient_global: Ingredient,
        second_dish_category: DishCategory,
    ) -> None:
        url = self.get_detail_url(str(dish_user_with_ingredient.id))
        response = auth_telegram_api_client.put(
            url,
            data={
                'name': 'Updated Dish Name',
                'recipe': 'Updated description',
                'category': str(second_dish_category.id),
                'dish_ingredients': [
                    {'ingredient': str(ingredient_global.id), 'amount': '100.000', 'is_optional': False}
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Dish Name'
        assert response.data['recipe'] == 'Updated description'
        assert response.data['category']['id'] == str(second_dish_category.id)

    def test_authenticated_client_can_put_dish_adding_new_ingredient(
        self,
        auth_telegram_api_client: APIClient,
        dish_user_with_ingredient: Dish,
        ingredient_global: Ingredient,
        ingredient_user: Ingredient,
    ) -> None:
        url = self.get_detail_url(str(dish_user_with_ingredient.id))
        response = auth_telegram_api_client.put(
            url,
            data={
                'category': str(dish_user_with_ingredient.category.id),
                'name': dish_user_with_ingredient.name,
                'dish_ingredients': [
                    {'ingredient': str(ingredient_global.id), 'amount': '100.000', 'is_optional': False},
                    {'ingredient': str(ingredient_user.id), 'amount': '50.000', 'is_optional': True},
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['dish_ingredients']) == 2
        ingredient_ids = {item['ingredient']['id'] for item in response.data['dish_ingredients']}
        assert str(ingredient_global.id) in ingredient_ids
        assert str(ingredient_user.id) in ingredient_ids

    def test_authenticated_client_can_put_dish_updating_ingredient(
        self,
        auth_telegram_api_client: APIClient,
        dish_user_with_ingredient: Dish,
        ingredient_global: Ingredient,
    ) -> None:
        url = self.get_detail_url(str(dish_user_with_ingredient.id))
        response = auth_telegram_api_client.put(
            url,
            data={
                'category': str(dish_user_with_ingredient.category.id),
                'name': dish_user_with_ingredient.name,
                'dish_ingredients': [
                    {'ingredient': str(ingredient_global.id), 'amount': '250.500', 'is_optional': False},
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['dish_ingredients']) == 1
        item = response.data['dish_ingredients'][0]
        assert Decimal(item['amount']) == Decimal('250.500')
        assert item['is_optional'] is False

    def test_authenticated_client_cannot_put_dish_making_all_ingredients_optional(
        self,
        auth_telegram_api_client: APIClient,
        dish_user_with_ingredient: Dish,
        ingredient_global: Ingredient,
    ) -> None:
        url = self.get_detail_url(str(dish_user_with_ingredient.id))
        response = auth_telegram_api_client.put(
            url,
            data={
                'category': str(dish_user_with_ingredient.category.id),
                'name': dish_user_with_ingredient.name,
                'dish_ingredients': [
                    {'ingredient': str(ingredient_global.id), 'amount': '100.000', 'is_optional': True},
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_authenticated_client_cannot_put_dish_all_optional_after_adding(
        self,
        auth_telegram_api_client: APIClient,
        dish_user_with_ingredient: Dish,
        ingredient_global: Ingredient,
        ingredient_user: Ingredient,
    ) -> None:
        url = self.get_detail_url(str(dish_user_with_ingredient.id))
        response = auth_telegram_api_client.put(
            url,
            data={
                'category': str(dish_user_with_ingredient.category.id),
                'name': dish_user_with_ingredient.name,
                'dish_ingredients': [
                    {'ingredient': str(ingredient_global.id), 'amount': '100.000', 'is_optional': True},
                    {'ingredient': str(ingredient_user.id), 'amount': '50.000', 'is_optional': True},
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_authenticated_client_can_put_dish_removing_ingredient(
        self,
        auth_telegram_api_client: APIClient,
        dish_user_with_ingredient: Dish,
        ingredient_global: Ingredient,
        ingredient_user: Ingredient,
    ) -> None:
        DishIngredient.objects.create(
            dish=dish_user_with_ingredient,
            ingredient=ingredient_user,
            amount=Decimal('50.000'),
            is_optional=True,
        )
        url = self.get_detail_url(str(dish_user_with_ingredient.id))
        response = auth_telegram_api_client.put(
            url,
            data={
                'category': str(dish_user_with_ingredient.category.id),
                'name': dish_user_with_ingredient.name,
                'dish_ingredients': [
                    {'ingredient': str(ingredient_global.id), 'amount': '100.000', 'is_optional': False},
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['dish_ingredients']) == 1
        assert response.data['dish_ingredients'][0]['ingredient']['id'] == str(ingredient_global.id)
        assert not DishIngredient.objects.filter(dish=dish_user_with_ingredient, ingredient=ingredient_user).exists()

    def test_authenticated_client_cannot_put_nonexistent_dish(
        self,
        auth_telegram_api_client: APIClient,
        dish_category: DishCategory,
        ingredient_global: Ingredient,
    ) -> None:
        url = self.get_detail_url(str(uuid.uuid4()))
        response = auth_telegram_api_client.put(
            url,
            data={
                'category': str(dish_category.id),
                'name': 'nonexistent',
                'dish_ingredients': [
                    {'ingredient': str(ingredient_global.id), 'amount': '100.000', 'is_optional': False},
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_authenticated_client_cannot_put_another_users_dish(
        self,
        auth_telegram_api_client: APIClient,
        another_telegram_user: User,
        dish_category: DishCategory,
        ingredient_global: Ingredient,
    ) -> None:
        foreign = Dish.objects.create(
            name='foreign put dish',
            category=dish_category,
            owner=another_telegram_user,
        )
        response = auth_telegram_api_client.put(
            self.get_detail_url(str(foreign.id)),
            data={
                'category': str(dish_category.id),
                'name': 'foreign put dish',
                'dish_ingredients': [
                    {'ingredient': str(ingredient_global.id), 'amount': '100.000', 'is_optional': False},
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_authenticated_client_cannot_put_global_dish(
        self,
        auth_telegram_api_client: APIClient,
        dish_user_with_ingredient: Dish,
        dish_global: Dish,
        ingredient_global: Ingredient,
    ) -> None:
        """Global dishes (owner=None) must not be modifiable by any user."""
        response = auth_telegram_api_client.put(
            self.get_detail_url(str(dish_global.id)),
            data={
                'category': str(dish_global.category.id),
                'name': dish_global.name,
                'dish_ingredients': [
                    {'ingredient': str(ingredient_global.id), 'amount': '100.000', 'is_optional': False},
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        dish_global.refresh_from_db()
        assert dish_global.owner is None

    def test_authenticated_client_cannot_put_dish_with_nonexistent_ingredient(
        self,
        auth_telegram_api_client: APIClient,
        dish_user_with_ingredient: Dish,
    ) -> None:
        response = auth_telegram_api_client.put(
            self.get_detail_url(str(dish_user_with_ingredient.id)),
            data={
                'category': str(dish_user_with_ingredient.category.id),
                'name': dish_user_with_ingredient.name,
                'dish_ingredients': [
                    {'ingredient': str(uuid.uuid4()), 'amount': '100.000', 'is_optional': False},
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_authenticated_client_cannot_put_dish_with_duplicate_ingredients(
        self,
        auth_telegram_api_client: APIClient,
        dish_user_with_ingredient: Dish,
        ingredient_global: Ingredient,
    ) -> None:
        response = auth_telegram_api_client.put(
            self.get_detail_url(str(dish_user_with_ingredient.id)),
            data={
                'category': str(dish_user_with_ingredient.category.id),
                'name': dish_user_with_ingredient.name,
                'dish_ingredients': [
                    {'ingredient': str(ingredient_global.id), 'amount': '100.000', 'is_optional': False},
                    {'ingredient': str(ingredient_global.id), 'amount': '50.000', 'is_optional': True},
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_authenticated_client_can_delete_own_dish(
        self, auth_telegram_api_client: APIClient, dish_user: Dish
    ) -> None:
        url = self.get_detail_url(str(dish_user.id))
        response = auth_telegram_api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        dish_user.refresh_from_db()
        assert not dish_user.is_active
        assert auth_telegram_api_client.get(url).status_code == status.HTTP_404_NOT_FOUND

    def test_authenticated_client_cannot_delete_global_dish(
        self, auth_telegram_api_client: APIClient, dish_global: Dish
    ) -> None:
        url = self.get_detail_url(str(dish_global.id))
        response = auth_telegram_api_client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        dish_global.refresh_from_db()
        assert dish_global.is_active

    def test_authenticated_client_cannot_delete_another_users_dish(
        self,
        auth_telegram_api_client: APIClient,
        another_telegram_user: User,
        dish_category: DishCategory,
    ) -> None:
        foreign = Dish.objects.create(
            name='foreign dish abc',
            category=dish_category,
            owner=another_telegram_user,
        )
        response = auth_telegram_api_client.delete(self.get_detail_url(str(foreign.id)))
        assert response.status_code == status.HTTP_404_NOT_FOUND
        foreign.refresh_from_db()
        assert foreign.is_active

    def test_anon_client_cannot_delete_dish(self, api_client: APIClient, dish_user: Dish) -> None:
        url = self.get_detail_url(str(dish_user.id))
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        dish_user.refresh_from_db()
        assert dish_user.is_active

    def test_delete_dish_also_removes_dish_ingredients(
        self, auth_telegram_api_client: APIClient, dish_user_with_ingredient: Dish, ingredient_global: Ingredient
    ) -> None:
        dish_id = dish_user_with_ingredient.id
        assert DishIngredient.objects.filter(dish_id=dish_id).exists()
        url = self.get_detail_url(str(dish_id))
        response = auth_telegram_api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not DishIngredient.objects.filter(dish_id=dish_id).exists()

    def test_authenticated_client_cannot_put_dish_with_duplicate_name(
        self,
        auth_telegram_api_client: APIClient,
        dish_user_with_ingredient: Dish,
        ingredient_global: Ingredient,
        dish_category: DishCategory,
        telegram_user: User,
    ) -> None:
        existing = Dish.objects.create(name='Already Taken Name', category=dish_category, owner=telegram_user)
        url = self.get_detail_url(str(dish_user_with_ingredient.id))
        response = auth_telegram_api_client.put(
            url,
            data={
                'category': str(dish_category.id),
                'name': existing.name,
                'dish_ingredients': [
                    {'ingredient': str(ingredient_global.id), 'amount': '100.000', 'is_optional': False},
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        dish_user_with_ingredient.refresh_from_db()
        assert dish_user_with_ingredient.name != existing.name

    def test_authenticated_client_cannot_put_dish_with_another_users_ingredient(
        self,
        auth_telegram_api_client: APIClient,
        dish_user_with_ingredient: Dish,
        ingredient_data: list[dict],
        another_telegram_user: User,
    ) -> None:
        foreign_ingredient = Ingredient.objects.create(**{**ingredient_data[2], 'owner': another_telegram_user})
        url = self.get_detail_url(str(dish_user_with_ingredient.id))
        response = auth_telegram_api_client.put(
            url,
            data={
                'category': str(dish_user_with_ingredient.category.id),
                'name': dish_user_with_ingredient.name,
                'dish_ingredients': [
                    {'ingredient': str(foreign_ingredient.id), 'amount': '100.000', 'is_optional': False},
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_method_not_allowed(self, auth_telegram_api_client: APIClient, dish_user: Dish) -> None:
        url = self.get_detail_url(str(dish_user.id))
        response = auth_telegram_api_client.patch(url, data={}, format='json')
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestDishCategoryFilterCaseInsensitive:
    list_url = reverse('api_v1:dishes:dishes:dish-category-list')

    def test_icontains_finds_by_lowercase(
        self, auth_telegram_api_client: APIClient, dish_category: DishCategory
    ) -> None:
        dish_category.name = 'Супы'
        dish_category.save(update_fields=['name'])
        response = auth_telegram_api_client.get(self.list_url, data={'name__icontains': 'супы'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_icontains_finds_by_uppercase(
        self, auth_telegram_api_client: APIClient, dish_category: DishCategory
    ) -> None:
        dish_category.name = 'Супы'
        dish_category.save(update_fields=['name'])
        response = auth_telegram_api_client.get(self.list_url, data={'name__icontains': 'СУПЫ'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_icontains_finds_partial_match(
        self, auth_telegram_api_client: APIClient, dish_category: DishCategory
    ) -> None:
        dish_category.name = 'Первые блюда'
        dish_category.save(update_fields=['name'])
        response = auth_telegram_api_client.get(self.list_url, data={'name__icontains': 'перв'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_icontains_returns_empty_on_no_match(
        self, auth_telegram_api_client: APIClient, dish_category: DishCategory
    ) -> None:
        response = auth_telegram_api_client.get(self.list_url, data={'name__icontains': 'zzzzNotExist'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0

    def test_icontains_latin_case_insensitive(
        self, auth_telegram_api_client: APIClient, dish_category: DishCategory
    ) -> None:
        dish_category.name = 'Soups'
        dish_category.save(update_fields=['name'])
        response = auth_telegram_api_client.get(self.list_url, data={'name__icontains': 'soups'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1


class TestDishFilterCaseInsensitive:
    list_url = reverse('api_v1:dishes:dishes:dish-list')

    def test_icontains_finds_by_lowercase(self, auth_telegram_api_client: APIClient, dish_global: Dish) -> None:
        dish_global.name = 'Борщ Украинский'
        dish_global.save(update_fields=['name'])
        response = auth_telegram_api_client.get(self.list_url, data={'name__icontains': 'борщ'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_icontains_finds_by_uppercase(self, auth_telegram_api_client: APIClient, dish_global: Dish) -> None:
        dish_global.name = 'Борщ Украинский'
        dish_global.save(update_fields=['name'])
        response = auth_telegram_api_client.get(self.list_url, data={'name__icontains': 'БОРЩ'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_icontains_finds_partial_middle_match(self, auth_telegram_api_client: APIClient, dish_global: Dish) -> None:
        dish_global.name = 'Борщ Украинский'
        dish_global.save(update_fields=['name'])
        response = auth_telegram_api_client.get(self.list_url, data={'name__icontains': 'украин'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_icontains_returns_empty_on_no_match(self, auth_telegram_api_client: APIClient, dish_global: Dish) -> None:
        response = auth_telegram_api_client.get(self.list_url, data={'name__icontains': 'zzzzNotExist'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0

    def test_icontains_latin_case_insensitive(self, auth_telegram_api_client: APIClient, dish_global: Dish) -> None:
        dish_global.name = 'Caesar Salad'
        dish_global.save(update_fields=['name'])
        response = auth_telegram_api_client.get(self.list_url, data={'name__icontains': 'caesar'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
