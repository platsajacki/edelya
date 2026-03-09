from django.db.models import QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.planning.api.serializers.cooking import CookingEventSerializer

# from core.base.decorators import extend_schema_view_from_class
from apps.planning.api.services.cooking.cooking_event_creator import CookingEventCreator
from apps.planning.api.services.cooking.cooking_event_updater import CookingEventUpdater
from apps.planning.models import CookingEvent
from core.base.permissions import OwnerObjectPermission


class CookingEventViewSet(ModelViewSet):
    queryset = CookingEvent.objects.none()
    serializer_class = CookingEventSerializer
    permission_classes = [IsAuthenticated & OwnerObjectPermission]
    http_method_names = ['get', 'post', 'patchdelete', 'head', 'options']
    lookup_url_kwarg = 'cooking_event_id'

    def get_queryset(self) -> QuerySet[CookingEvent]:
        if self.request.user.is_authenticated:
            return CookingEvent.objects.for_user(self.request.user)
        return CookingEvent.objects.none()

    def perform_create(self, serializer: CookingEventSerializer) -> None:
        return CookingEventCreator(serializer)()

    def perform_update(self, serializer: CookingEventSerializer) -> None:
        return CookingEventUpdater(serializer)()
