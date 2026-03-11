from typing import TYPE_CHECKING, Any

from django.apps import apps
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import UserManager as DjangoUserManager

if TYPE_CHECKING:
    from apps.users.models import User


class UserManager(DjangoUserManager):
    def _create_user_object(
        self,
        username: str | None = None,
        email: str | None = None,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        telegram_id = extra_fields.get('telegram_id')
        if not username and not telegram_id:
            raise ValueError('The given username or telegram_id must be set')
        GlobalUserModel = apps.get_model(self.model._meta.app_label, self.model._meta.object_name)
        if email:
            email = self.normalize_email(email)
        if username:
            username = GlobalUserModel.normalize_username(username)
        user = self.model(username=username, telegram_id=telegram_id, email=email, **extra_fields)
        if password:
            user.password = make_password(password)
        else:
            user.set_unusable_password()
        return user  # type: ignore[return-value]
