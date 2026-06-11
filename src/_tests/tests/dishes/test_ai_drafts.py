import pytest
from pytest_mock import MockType

from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from apps.dishes.api.serializers.ai_drafts import DishAIDraftSerializer
from apps.dishes.data_types import DishPayloadData
from apps.dishes.models import Dish, DishAIDraft, DishIngredient, Ingredient, IngredientCategory
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


class TestDishAIDraftViewSetCreateDish:
    def get_create_dish_url(self, id: str) -> str:
        return reverse('api_v1:dishes:dishes:dish-ai-draft-create-dish', kwargs={'draft_id': id})

    def post_create_dish(
        self,
        api_client: APIClient,
        draft: DishAIDraft,
        payload: DishPayloadData,
    ) -> Response:
        return api_client.post(
            self.get_create_dish_url(str(draft.id)),
            data={'payload': payload},
            format='json',
        )

    def test_creates_dish_from_parsed_draft_with_new_ingredient(
        self,
        auth_telegram_api_client: APIClient,
        parsed_dish_ai_draft: DishAIDraft,
        valid_dish_payload: DishPayloadData,
        telegram_user: User,
    ) -> None:
        response = self.post_create_dish(auth_telegram_api_client, parsed_dish_ai_draft, valid_dish_payload)
        assert response.status_code == status.HTTP_201_CREATED, response.data
        dish = Dish.objects.get(id=response.data['id'])
        ingredient = Ingredient.objects.get(name='Свекла', owner=telegram_user)
        dish_ingredient = DishIngredient.objects.get(dish=dish, ingredient=ingredient)
        parsed_dish_ai_draft.refresh_from_db()
        assert dish.owner == telegram_user
        assert dish.name == valid_dish_payload['name']
        assert dish.recipe == valid_dish_payload['recipe']
        assert str(dish.category_id) == valid_dish_payload['category']
        assert str(ingredient.category_id) == valid_dish_payload['ingredients'][0]['category']
        assert ingredient.base_unit == valid_dish_payload['ingredients'][0]['base_unit']
        assert dish_ingredient.amount == Decimal('300.000')
        assert dish_ingredient.is_optional is False
        assert parsed_dish_ai_draft.status == DishAIDraftStatus.DISH_CREATED
        assert parsed_dish_ai_draft.payload == valid_dish_payload
        assert parsed_dish_ai_draft.created_dish_id == dish.id

    def test_creates_dish_from_parsed_draft_with_existing_ingredient(
        self,
        auth_telegram_api_client: APIClient,
        parsed_dish_ai_draft: DishAIDraft,
        valid_dish_payload: DishPayloadData,
        ingredient_user: Ingredient,
    ) -> None:
        payload = deepcopy(valid_dish_payload)
        payload['ingredients'][0] = {
            'ingredient': str(ingredient_user.id),
            'name': ingredient_user.name,
            'category': str(ingredient_user.category_id),
            'base_unit': ingredient_user.base_unit,
            'amount': 75.5,
            'is_optional': False,
            'new': False,
            'suggested_ids': [],
        }
        ingredient_count = Ingredient.objects.count()

        response = self.post_create_dish(auth_telegram_api_client, parsed_dish_ai_draft, payload)
        assert response.status_code == status.HTTP_201_CREATED, response.data

        dish = Dish.objects.get(id=response.data['id'])
        dish_ingredient = DishIngredient.objects.get(dish=dish)
        assert Ingredient.objects.count() == ingredient_count
        assert dish_ingredient.ingredient == ingredient_user
        assert dish_ingredient.amount == Decimal('75.500')
        assert dish_ingredient.is_optional is False

    def test_creates_dish_from_parsed_draft_with_mixed_ingredients(
        self,
        auth_telegram_api_client: APIClient,
        parsed_dish_ai_draft: DishAIDraft,
        valid_dish_payload: DishPayloadData,
        ingredient_user: Ingredient,
    ) -> None:
        payload = deepcopy(valid_dish_payload)
        payload['ingredients'] = [
            {
                'ingredient': str(ingredient_user.id),
                'name': ingredient_user.name,
                'category': str(ingredient_user.category_id),
                'base_unit': ingredient_user.base_unit,
                'amount': 75.0,
                'is_optional': False,
                'new': False,
                'suggested_ids': [],
            },
            {
                **valid_dish_payload['ingredients'][0],
                'name': 'Морковь',
                'amount': 50.0,
                'is_optional': True,
            },
        ]
        response = self.post_create_dish(auth_telegram_api_client, parsed_dish_ai_draft, payload)
        assert response.status_code == status.HTTP_201_CREATED, response.data
        dish = Dish.objects.get(id=response.data['id'])
        dish_ingredients = {
            item.ingredient.name: item for item in DishIngredient.objects.select_related('ingredient').filter(dish=dish)
        }
        assert set(dish_ingredients) == {ingredient_user.name, 'Морковь'}
        assert dish_ingredients[ingredient_user.name].amount == Decimal('75.000')
        assert dish_ingredients[ingredient_user.name].is_optional is False
        assert dish_ingredients['Морковь'].amount == Decimal('50.000')
        assert dish_ingredients['Морковь'].is_optional is True

    def test_duplicate_dish_name_gets_ai_suffix(
        self,
        auth_telegram_api_client: APIClient,
        parsed_dish_ai_draft: DishAIDraft,
        valid_dish_payload: DishPayloadData,
        dish_user: Dish,
    ) -> None:
        payload = deepcopy(valid_dish_payload)
        payload['name'] = dish_user.name

        response = self.post_create_dish(auth_telegram_api_client, parsed_dish_ai_draft, payload)
        assert response.status_code == status.HTTP_201_CREATED

        dish = Dish.objects.get(id=response.data['id'])
        assert dish.name == f'{dish_user.name} (AI)'

    def test_duplicate_ai_suffix_name_returns_bad_request(
        self,
        auth_telegram_api_client: APIClient,
        parsed_dish_ai_draft: DishAIDraft,
        valid_dish_payload: DishPayloadData,
        dish_user: Dish,
    ) -> None:
        Dish.objects.create(
            name=f'{dish_user.name} (AI)',
            category=dish_user.category,
            owner=dish_user.owner,
        )
        payload = deepcopy(valid_dish_payload)
        payload['name'] = dish_user.name
        response = self.post_create_dish(auth_telegram_api_client, parsed_dish_ai_draft, payload)
        parsed_dish_ai_draft.refresh_from_db()
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert parsed_dish_ai_draft.status == DishAIDraftStatus.PARSED
        assert parsed_dish_ai_draft.created_dish_id is None

    def test_cannot_create_dish_from_not_parsed_draft(
        self,
        auth_telegram_api_client: APIClient,
        dish_ai_draft: DishAIDraft,
        valid_dish_payload: DishPayloadData,
    ) -> None:
        response = self.post_create_dish(auth_telegram_api_client, dish_ai_draft, valid_dish_payload)
        dish_ai_draft.refresh_from_db()
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Dish.objects.filter(name=valid_dish_payload['name']).exists() is False
        assert dish_ai_draft.status == DishAIDraftStatus.PROCESSING
        assert dish_ai_draft.created_dish_id is None

    def test_cannot_create_dish_with_foreign_existing_ingredient(
        self,
        auth_telegram_api_client: APIClient,
        parsed_dish_ai_draft: DishAIDraft,
        valid_dish_payload: DishPayloadData,
        ingredient_data: list[dict],
        another_telegram_user: User,
    ) -> None:
        foreign_ingredient = Ingredient.objects.create(**{**ingredient_data[2], 'owner': another_telegram_user})
        payload = deepcopy(valid_dish_payload)
        payload['ingredients'][0] = {
            'ingredient': str(foreign_ingredient.id),
            'name': foreign_ingredient.name,
            'category': str(foreign_ingredient.category_id),
            'base_unit': foreign_ingredient.base_unit,
            'amount': 100.0,
            'is_optional': False,
            'new': False,
            'suggested_ids': [],
        }
        response = self.post_create_dish(auth_telegram_api_client, parsed_dish_ai_draft, payload)
        parsed_dish_ai_draft.refresh_from_db()
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Dish.objects.filter(name=payload['name']).exists() is False
        assert parsed_dish_ai_draft.status == DishAIDraftStatus.PARSED
        assert parsed_dish_ai_draft.created_dish_id is None

    def test_cannot_create_dish_with_missing_existing_ingredient(
        self,
        auth_telegram_api_client: APIClient,
        parsed_dish_ai_draft: DishAIDraft,
        valid_dish_payload: DishPayloadData,
    ) -> None:
        payload = deepcopy(valid_dish_payload)
        payload['ingredients'][0] = {
            **payload['ingredients'][0],
            'ingredient': str(uuid4()),
            'new': False,
        }
        response = self.post_create_dish(auth_telegram_api_client, parsed_dish_ai_draft, payload)
        parsed_dish_ai_draft.refresh_from_db()
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Dish.objects.filter(name=payload['name']).exists() is False
        assert parsed_dish_ai_draft.status == DishAIDraftStatus.PARSED
        assert parsed_dish_ai_draft.created_dish_id is None

    def test_all_optional_ingredients_rolls_back_created_objects(
        self,
        auth_telegram_api_client: APIClient,
        parsed_dish_ai_draft: DishAIDraft,
        valid_dish_payload: DishPayloadData,
    ) -> None:
        payload = deepcopy(valid_dish_payload)
        payload['ingredients'][0]['is_optional'] = True
        ingredient_count = Ingredient.objects.count()
        response = self.post_create_dish(auth_telegram_api_client, parsed_dish_ai_draft, payload)
        parsed_dish_ai_draft.refresh_from_db()
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Ingredient.objects.count() == ingredient_count
        assert Dish.objects.filter(name=payload['name']).exists() is False
        assert parsed_dish_ai_draft.status == DishAIDraftStatus.PARSED
        assert parsed_dish_ai_draft.created_dish_id is None

    @pytest.mark.parametrize(
        ('field', 'value', 'expected_status'),
        [
            ('base_unit', 'bad_unit', status.HTTP_400_BAD_REQUEST),
            ('category', '00000000-0000-0000-0000-000000000001', status.HTTP_400_BAD_REQUEST),
            ('ingredient', '00000000-0000-0000-0000-000000000002', status.HTTP_400_BAD_REQUEST),
        ],
    )
    def test_cannot_create_dish_with_invalid_new_ingredient(
        self,
        auth_telegram_api_client: APIClient,
        parsed_dish_ai_draft: DishAIDraft,
        valid_dish_payload: DishPayloadData,
        field: str,
        value: str,
        expected_status: int,
    ) -> None:
        payload = deepcopy(valid_dish_payload)
        payload['ingredients'][0][field] = value  # type: ignore[literal-required]
        response = self.post_create_dish(auth_telegram_api_client, parsed_dish_ai_draft, payload)
        parsed_dish_ai_draft.refresh_from_db()
        assert response.status_code == expected_status
        assert Dish.objects.filter(name=payload['name']).exists() is False
        assert parsed_dish_ai_draft.status == DishAIDraftStatus.PARSED
        assert parsed_dish_ai_draft.created_dish_id is None

    def test_cannot_create_dish_with_inactive_new_ingredient_category(
        self,
        auth_telegram_api_client: APIClient,
        parsed_dish_ai_draft: DishAIDraft,
        valid_dish_payload: DishPayloadData,
        ingredient_category: IngredientCategory,
    ) -> None:
        ingredient_category.is_active = False
        ingredient_category.save(update_fields=['is_active'])
        response = self.post_create_dish(auth_telegram_api_client, parsed_dish_ai_draft, valid_dish_payload)
        parsed_dish_ai_draft.refresh_from_db()
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Dish.objects.filter(name=valid_dish_payload['name']).exists() is False
        assert parsed_dish_ai_draft.status == DishAIDraftStatus.PARSED
        assert parsed_dish_ai_draft.created_dish_id is None
