from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

api_urlpatterns_v1 = [
    path('auth/', include(('apps.a12n.urls', 'a12n'), namespace='a12n')),
    path('', include(('apps.users.api.urls', 'users'), namespace='users')),
    path('', include(('apps.dishes.api.urls', 'dishes'), namespace='dishes')),
    path('', include(('apps.planning.api.urls', 'planning'), namespace='planning')),
    path('', include(('apps.shopping.api.urls', 'shopping'), namespace='shopping')),
    path('', include(('apps.subscriptions.api.urls', 'subscriptions'), namespace='subscriptions')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include((api_urlpatterns_v1, 'api_v1')), name='api_v1'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
