from django.urls import path

from apps.a12n.views import TelegramTokenObtainPairView, TokenRefreshView

app_name = 'a12n'

urlpatterns = [
    path('token/telegram/', TelegramTokenObtainPairView.as_view(), name='token_telegram_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
