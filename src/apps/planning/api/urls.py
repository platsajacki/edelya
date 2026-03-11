from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.planning.api.views.cooking import CookingEventViewSet
from apps.planning.api.views.meal_plan_items import MealPlanItemViewSet
from apps.planning.api.views.weeks import WeekDishesAPIView

app_name = 'planning'

planning = DefaultRouter()
planning.register(r'cooking-events', CookingEventViewSet, basename='cooking-event')
planning.register(r'meal-plan-items', MealPlanItemViewSet, basename='meal-plan-item')

urlpatterns = [
    path('planning/year/<int:year>/week/<int:week>/', WeekDishesAPIView.as_view(), name='week-dishes'),
    path('planning/', include((planning.urls, 'cooking'), namespace='cooking')),
]
