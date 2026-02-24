from django.urls import path

from a12n.views import TelegramTokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('token/telegram/', TelegramTokenObtainPairView.as_view(), name='token_telegram_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
