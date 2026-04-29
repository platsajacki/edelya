from typing import Any

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.subscriptions.api.schemas import SubscriptionViewSetSchema
from apps.subscriptions.api.serializers.subscriptions import SubscriptionSerializer, SubscriptionTariffSelectSerializer
from apps.subscriptions.api.services.subscription_canceller import SubscriptionCanceller
from apps.subscriptions.api.services.subscription_getter import SubscriptionGetter
from apps.subscriptions.api.services.subscription_resumer import SubscriptionResumer
from apps.subscriptions.api.services.tariff_selector import TariffSelector
from apps.subscriptions.api.services.trial_startrer import TrialStarter
from core.base.decorators import extend_schema_view_from_class


@extend_schema_view_from_class(SubscriptionViewSetSchema)
class SubscriptionViewSet(GenericViewSet):
    serializer_class = SubscriptionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self) -> type[SubscriptionSerializer]:
        if self.action == self.select_tariff.__name__:
            return SubscriptionTariffSelectSerializer
        return self.serializer_class

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return SubscriptionGetter(request=request, serializer_class=self.get_serializer_class())()

    @action(detail=False, methods=['post'], url_path='start-trial')
    def start_trial(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return TrialStarter(request=request, serializer_class=self.get_serializer_class())()

    @action(detail=False, methods=['post'], url_path='select-tariff')
    def select_tariff(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        return TariffSelector(request=request, serializer=serializer)()

    @action(detail=False, methods=['post'], url_path='cancel')
    def cancel(self, request: Request) -> Response:
        return SubscriptionCanceller(request=request, serializer_class=self.get_serializer_class())()

    @action(detail=False, methods=['post'], url_path='resume')
    def resume(self, request: Request) -> Response:
        return SubscriptionResumer(request=request, serializer_class=self.get_serializer_class())()
