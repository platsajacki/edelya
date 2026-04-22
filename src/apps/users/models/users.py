from typing import TYPE_CHECKING

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import ASCIIUsernameValidator
from django.db import models

from apps.users.managers import UserManager
from core.base.abstract_models import BaseModel
from core.base.validators import dict_validator

ascii_username_validator = ASCIIUsernameValidator()

if TYPE_CHECKING:
    from apps.subscriptions.models import Subscription


class User(BaseModel, AbstractUser):
    if TYPE_CHECKING:
        subscription: Subscription

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
    onboarding_data = models.JSONField(
        verbose_name='Onboarding Data',
        default=dict,
        validators=[dict_validator],
    )

    objects: UserManager = UserManager()  # type: ignore[misc]

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self) -> str:
        return f'ID: {self.id}'
