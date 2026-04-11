from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.subscriptions.api.schemas import TariffViewSetSchema
from apps.subscriptions.api.serializers.tariffs import TariffSerializer
from apps.subscriptions.models import Tariff
from core.base.decorators import extend_schema_view_from_class


@extend_schema_view_from_class(TariffViewSetSchema)
class TariffViewSet(ReadOnlyModelViewSet):
    queryset = Tariff.objects.published().actived()
    serializer_class = TariffSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'tariff_id'
