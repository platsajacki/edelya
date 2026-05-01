from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.subscriptions.api.views.payment_methods import PaymentMethodViewSet
from apps.subscriptions.api.views.subscriptions import SubscriptionViewSet
from apps.subscriptions.api.views.tariffs import TariffViewSet
from apps.subscriptions.api.views.webhooks import YookassaWebhookView

app_name = 'subscriptions'

router = DefaultRouter()
router.register(r'tariffs', TariffViewSet, basename='tariff')
router.register(r'', SubscriptionViewSet, basename='subscription')

urlpatterns = [
    path(
        'subscriptions/',
        include(
            (router.urls, 'subscriptions'),
            namespace='subscriptions',
        ),
    ),
    path(
        'subscriptions/payment-method/',
        PaymentMethodViewSet.as_view(),
        name='payment-method',
    ),
    path(
        'subscriptions/webhooks/yookassa/',
        YookassaWebhookView.as_view(),
        name='yookassa-webhook',
    ),
]
