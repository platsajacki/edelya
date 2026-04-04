from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.shopping.api.views.shopping_list import ShoppingListItemViewSet, ShoppingListViewSet

app_name = 'shopping'

router = DefaultRouter()
router.register(r'shopping-lists', ShoppingListViewSet, basename='shopping-list')

item_router = DefaultRouter()
item_router.register(r'items', ShoppingListItemViewSet, basename='shopping-list-item')

urlpatterns = [
    path(
        'shopping/',
        include(
            (
                [
                    *router.urls,
                    path('shopping-lists/<uuid:shopping_list_id>/', include(item_router.urls)),
                ],
                'shopping',
            ),
            namespace='shopping',
        ),
    ),
]
