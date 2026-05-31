from django.db.models import Model
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.dishes.models.ai_drafts import DishAIDraft
from core.base.exceptions import AIRecipeLimitExceeded


class OwnerObjectPermission(BasePermission):
    def has_object_permission(self, request: Request, view: APIView, obj: Model) -> bool:
        if not hasattr(obj, 'owner'):
            return False
        if obj.owner is None and request.method in SAFE_METHODS:
            return True
        return obj.owner == request.user


class CanUseBaseFeatures(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        subscription = getattr(request.user, 'subscription', None)
        if subscription is None:
            return False
        tariff = getattr(subscription, 'tariff', None)
        if tariff is None:
            return False
        return bool(tariff.can_use_base_features)

    def has_object_permission(self, request: Request, view: APIView, obj: Model) -> bool:
        return self.has_permission(request, view)


class HasActiveTrial(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        subscription = getattr(request.user, 'subscription', None)
        if subscription is None:
            return False
        return subscription.is_active and subscription.tariff.is_trial_tariff

    def has_object_permission(self, request: Request, view: APIView, obj: Model) -> bool:
        return self.has_permission(request, view)


class CanCreateAIRecipes(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        subscription = getattr(request.user, 'subscription', None)
        if subscription is None:
            return False
        tariff = getattr(subscription, 'tariff', None)
        if tariff is None:
            return False
        if not tariff.can_create_ai_recipes:
            return False
        if not DishAIDraft.objects.can_create_new_draft(subscription):
            raise AIRecipeLimitExceeded(reset_at=subscription.ended_at)
        return True

    def has_object_permission(self, request: Request, view: APIView, obj: Model) -> bool:
        return self.has_permission(request, view)
