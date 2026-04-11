from django.db.models import QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.dishes.api.schemas import IngredientCategoryViewSetSchema, IngredientViewSetSchema
from apps.dishes.api.serializers.ingredients import IngredientCategorySerializer, IngredientSerializer
from apps.dishes.api.views.filters.ingredient import IngredientCategoryFilter, IngredientFilter
from apps.dishes.models import Ingredient, IngredientCategory
from apps.users.models import User
from core.base.decorators import extend_schema_view_from_class
from core.base.permissions import CanUseBaseFeatures, OwnerObjectPermission


@extend_schema_view_from_class(IngredientCategoryViewSetSchema)
class IngredientCategoryViewSet(ReadOnlyModelViewSet):
    queryset = IngredientCategory.objects.actived()
    serializer_class = IngredientCategorySerializer
    permission_classes = [IsAuthenticated & CanUseBaseFeatures]
    filterset_class = IngredientCategoryFilter
    lookup_url_kwarg = 'ingredient_category_id'


@extend_schema_view_from_class(IngredientViewSetSchema)
class IngredientViewSet(ModelViewSet):
    queryset = Ingredient.objects.none()
    serializer_class = IngredientSerializer
    permission_classes = [IsAuthenticated & OwnerObjectPermission & CanUseBaseFeatures]
    filterset_class = IngredientFilter
    lookup_url_kwarg = 'ingredient_id'

    def get_queryset(self) -> QuerySet[Ingredient]:
        if isinstance(self.request.user, User) and self.request.user.is_authenticated:
            return Ingredient.objects.for_user(self.request.user)
        return Ingredient.objects.none()

    def perform_destroy(self, instance: Ingredient) -> None:
        instance.deactivate()
