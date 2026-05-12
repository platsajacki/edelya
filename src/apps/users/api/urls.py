from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.users.api.views.legal_docs import PrivacyPolicyVersionViewSet, TermsOfServiceVersionViewSet
from apps.users.api.views.users import OnboardingDataViewSet

router = SimpleRouter(trailing_slash=True)
router.register(r'legal/terms-of-service', TermsOfServiceVersionViewSet, basename='terms-of-service')
router.register(r'legal/privacy-policy', PrivacyPolicyVersionViewSet, basename='privacy-policy')

urlpatterns = [
    path('users/me/onboarding-data/', OnboardingDataViewSet.as_view(), name='user-onboarding-data'),
    path('', include(router.urls)),
]
