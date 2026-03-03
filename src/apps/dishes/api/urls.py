from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.dishes.api.views.dishes import DishCategoryViewSet, DishViewSet
from apps.dishes.api.views.ingredients import IngredientCategoryViewSet, IngredientViewSet

app_name = 'dishes'

ingredients_router = DefaultRouter()
ingredients_router.register(r'ingredient-categories', IngredientCategoryViewSet, basename='ingredient-category')
ingredients_router.register(r'ingredients', IngredientViewSet, basename='ingredient')

dishes_router = DefaultRouter()
dishes_router.register(r'dish-categories', DishCategoryViewSet, basename='dish-category')
dishes_router.register(r'dishes', DishViewSet, basename='dish')

urlpatterns = [
    path('', include((ingredients_router.urls, 'ingredients'), namespace='ingredients')),
    path('', include((dishes_router.urls, 'dishes'), namespace='dishes')),
]
