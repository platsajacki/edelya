from django.db.models import Model
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class OwnerObjectPermission(BasePermission):
    def has_object_permission(self, request: Request, view: APIView, obj: Model) -> bool:
        return hasattr(obj, 'owner') and obj.owner == request.user
