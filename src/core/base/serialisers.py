from rest_framework.exceptions import NotAuthenticated, NotFound
from rest_framework.fields import HiddenField

from apps.shopping.models import ShoppingList
from apps.users.models import User


class CurrentShoppingList:
    requires_context = True

    def __call__(self, serializer_field: HiddenField) -> ShoppingList:
        request = serializer_field.context.get('request')
        if not request or not isinstance(request.user, User):
            raise NotAuthenticated('User is not authenticated')
        shopping_list_id = serializer_field.context['view'].kwargs.get('shopping_list_id')
        if not shopping_list_id:
            raise NotFound('Shopping list ID is not provided in the URL')
        try:
            shopping_list = ShoppingList.objects.filter(owner=request.user).get(pk=shopping_list_id)
        except ShoppingList.DoesNotExist as e:
            raise NotFound('Shopping list does not exist or does not belong to the user') from e
        return shopping_list

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}()'
