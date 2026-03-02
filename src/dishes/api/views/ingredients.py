from django.db.models import QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from app.base.decorators import extend_schema_view_from_class
from app.base.permissions import OwnerObjectPermission
from dishes.api.schemas import IngredientCategoryViewSetSchema, IngredientViewSetSchema
from dishes.api.serializers.ingredients import IngredientCategorySerializer, IngredientSerializer
from dishes.api.views.filters.ingredient import IngredientCategoryFilter, IngredientFilter
from dishes.models import Ingredient, IngredientCategory
from users.models import User


@extend_schema_view_from_class(IngredientCategoryViewSetSchema)
class IngredientCategoryViewSet(ReadOnlyModelViewSet):
    queryset = IngredientCategory.objects.actived()
    serializer_class = IngredientCategorySerializer
    permission_classes = [IsAuthenticated]
    filterset_class = IngredientCategoryFilter


@extend_schema_view_from_class(IngredientViewSetSchema)
class IngredientViewSet(ModelViewSet):
    queryset = Ingredient.objects.none()
    serializer_class = IngredientSerializer
    permission_classes = [IsAuthenticated & OwnerObjectPermission]
    filterset_class = IngredientFilter

    def get_queryset(self) -> QuerySet[Ingredient]:
        if isinstance(self.request.user, User) and self.request.user.is_authenticated:
            return Ingredient.objects.for_user(self.request.user).with_category()
        return Ingredient.objects.none()

    def perform_destroy(self, instance: Ingredient) -> None:
        instance.deactivate()
