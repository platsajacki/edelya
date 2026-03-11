from django.urls import path

from apps.a12n.views import LoginTokenObtainPairView, TelegramTokenObtainPairView, TokenRefreshView

app_name = 'a12n'

urlpatterns = [
    path('token/login/', LoginTokenObtainPairView.as_view(), name='token_login_obtain_pair'),
    path('token/telegram/', TelegramTokenObtainPairView.as_view(), name='token_telegram_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
