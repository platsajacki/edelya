from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
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

    @action(detail=False, methods=['get'], url_path='trial-duration')
    def trial_duration(self, request: Request) -> Response:
        return Response({'trial_duration': Tariff.objects.trial_duration()})
