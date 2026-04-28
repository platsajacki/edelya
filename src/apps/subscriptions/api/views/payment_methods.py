from typing import Any

from django.db.models import QuerySet
from rest_framework.exceptions import NotFound
from rest_framework.generics import CreateAPIView, DestroyAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.subscriptions.api.schemas import PaymentMethodViewSetSchema
from apps.subscriptions.api.serializers.payment_methods import PaymentMethodSerializer
from apps.subscriptions.api.services.payment_method_binder import PaymentMethodBinder
from apps.subscriptions.models import PaymentMethod
from core.base.decorators import extend_schema_view_from_class


@extend_schema_view_from_class(PaymentMethodViewSetSchema)
class PaymentMethodViewSet(RetrieveAPIView, DestroyAPIView, CreateAPIView):
    queryset = PaymentMethod.objects.none()
    serializer_class = PaymentMethodSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        return PaymentMethod.objects.filter(user=self.request.user)

    def get_object(self) -> PaymentMethod:
        try:
            obj = self.get_queryset().get()
        except (PaymentMethod.DoesNotExist, PaymentMethod.MultipleObjectsReturned) as e:
            raise NotFound('No payment method found for the authenticated user.') from e
        return obj

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        result = PaymentMethodBinder(user=request.user)()
        return Response(result)
