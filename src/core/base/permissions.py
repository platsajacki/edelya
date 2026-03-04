from django.db.models import Model
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class OwnerObjectPermission(BasePermission):
    def has_object_permission(self, request: Request, view: APIView, obj: Model) -> bool:
        if not hasattr(obj, 'owner'):
            return False
        if obj.owner is None and request.method in SAFE_METHODS:
            return True
        return obj.owner == request.user
