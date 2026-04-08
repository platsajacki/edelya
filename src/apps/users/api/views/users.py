from rest_framework.exceptions import NotFound
from rest_framework.generics import RetrieveAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated

from apps.users.api.schemas import OnboardingDataViewSchema
from apps.users.api.serializers.users import OnboardingDataSerializer
from apps.users.models.users import User
from core.base.decorators import extend_schema_view_from_class


@extend_schema_view_from_class(OnboardingDataViewSchema)
class OnboardingDataViewSet(RetrieveAPIView, UpdateAPIView):
    queryset = User.objects.none()
    serializer_class = OnboardingDataSerializer
    http_method_names = ['get', 'patch']
    permission_classes = [IsAuthenticated]

    def get_object(self) -> User:
        if isinstance(self.request.user, User):
            return self.request.user
        raise NotFound('User not found')
