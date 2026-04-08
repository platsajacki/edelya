from django.urls import path

from apps.users.api.views.users import OnboardingDataViewSet

urlpatterns = [
    path('users/me/onboarding-data/', OnboardingDataViewSet.as_view(), name='user-onboarding-data'),
]
