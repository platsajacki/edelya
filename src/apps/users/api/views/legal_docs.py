from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.users.api.schemas import PrivacyPolicyVersionViewSetSchema, TermsOfServiceVersionViewSetSchema
from apps.users.api.serializers.legal_docs import (
    PrivacyPolicyVersionSerializer,
    TermsOfServiceVersionSerializer,
)
from apps.users.models.legal_docs import PrivacyPolicyVersion, TermsOfServiceVersion
from apps.users.models.managers.legal_docs import PrivacyPolicyVersionQuerySet, TermsOfServiceVersionQuerySet
from core.base.decorators import cache_viewset_actions, extend_schema_view_from_class
from core.constants import CACHE_LATEST_1H, CACHE_LIST_1H


@cache_viewset_actions([CACHE_LIST_1H, CACHE_LATEST_1H])
@extend_schema_view_from_class(TermsOfServiceVersionViewSetSchema)
class TermsOfServiceVersionViewSet(ListModelMixin, GenericViewSet):
    serializer_class = TermsOfServiceVersionSerializer
    authentication_classes: list = []
    permission_classes: list = []

    def get_queryset(self) -> TermsOfServiceVersionQuerySet:
        return TermsOfServiceVersion.objects.latest_first()

    @action(detail=False, methods=['get'], url_path='latest')
    def latest(self, request: Request) -> Response:
        instance = TermsOfServiceVersion.objects.current()
        if instance is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(instance).data)


@cache_viewset_actions([CACHE_LIST_1H, CACHE_LATEST_1H])
@extend_schema_view_from_class(PrivacyPolicyVersionViewSetSchema)
class PrivacyPolicyVersionViewSet(ListModelMixin, GenericViewSet):
    serializer_class = PrivacyPolicyVersionSerializer
    authentication_classes: list = []
    permission_classes: list = []

    def get_queryset(self) -> PrivacyPolicyVersionQuerySet:
        return PrivacyPolicyVersion.objects.latest_first()

    @action(detail=False, methods=['get'], url_path='latest')
    def latest(self, request: Request) -> Response:
        instance = PrivacyPolicyVersion.objects.current()
        if instance is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(instance).data)
