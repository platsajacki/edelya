from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import ASCIIUsernameValidator
from django.db import models

from apps.users.managers import UserManager
from core.base.abstract_models import BaseModel

ascii_username_validator = ASCIIUsernameValidator()


class User(BaseModel, AbstractUser):
    username = models.CharField(  # type: ignore[assignment]
        verbose_name='Username',
        max_length=150,
        help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.',
        validators=[ascii_username_validator],
        error_messages={
            'unique': 'A user with that username already exists.',
        },
        blank=True,
        null=True,
        unique=True,
    )
    telegram_id = models.CharField(
        verbose_name='Telegram ID',
        max_length=255,
        blank=True,
        null=True,
        unique=True,
    )
    telegram_name = models.CharField(
        verbose_name='Telegram Profile Name',
        max_length=255,
        blank=True,
        null=True,
    )
    telegram_username = models.CharField(
        verbose_name='Telegram Username',
        max_length=255,
        blank=True,
        null=True,
    )

    objects: UserManager = UserManager()  # type: ignore[misc]

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self) -> str:
        return f'ID: {self.id}'
