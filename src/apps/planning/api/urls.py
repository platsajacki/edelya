from django.urls import path

from apps.planning.api.views.weeks import WeekDishesAPIView

app_name = 'planning'

urlpatterns = [
    path('planning/year/<int:year>/week/<int:week>/', WeekDishesAPIView.as_view(), name='week-dishes'),
]
