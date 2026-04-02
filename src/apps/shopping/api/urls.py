from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.shopping.api.views.shopping_list import ShoppingListViewSet

app_name = 'shopping'

router = DefaultRouter()
router.register(r'shopping-lists', ShoppingListViewSet, basename='shopping-list')

urlpatterns = [
    path('shopping/', include((router.urls, 'shopping'), namespace='shopping')),
]
