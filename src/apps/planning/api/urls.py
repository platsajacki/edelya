from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.planning.api.views.cooking import CookingEventViewSet
from apps.planning.api.views.weeks import WeekDishesAPIView

app_name = 'planning'

cooking_router = DefaultRouter()
cooking_router.register(r'cooking-events', CookingEventViewSet, basename='cooking-event')

urlpatterns = [
    path('planning/year/<int:year>/week/<int:week>/', WeekDishesAPIView.as_view(), name='week-dishes'),
    path('planning/', include((cooking_router.urls, 'cooking'), namespace='cooking')),
]
