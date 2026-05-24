from typing import TYPE_CHECKING

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import ASCIIUsernameValidator
from django.db import models

from telebot.types import InputFile

from apps.users.managers import UserManager
from core.base.abstract_models import BaseModel
from core.base.validators import dict_validator
from core.telegram import EdelyaBotSender, TGKeyboard

if TYPE_CHECKING:
    from apps.subscriptions.models import Subscription

ascii_username_validator = ASCIIUsernameValidator()


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
    telegram_is_active = models.BooleanField(
        verbose_name='Telegram Active',
        default=True,
    )
    onboarding_data = models.JSONField(
        verbose_name='Onboarding Data',
        default=dict,
        validators=[dict_validator],
    )
    marketing_communications = models.BooleanField(
        verbose_name='Marketing Communications',
        default=False,
    )

    objects: UserManager = UserManager()  # type: ignore[misc]

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self) -> str:
        return f'ID: {self.id}'

    @property
    def is_telegram_active(self) -> bool:
        return self.telegram_id is not None and self.telegram_is_active

    def inactivate_telegram(self) -> None:
        self.telegram_is_active = False
        self.save(update_fields=['telegram_is_active'])

    def send_telegram_message(
        self,
        text: str,
        kb: TGKeyboard = None,
        parse_mode: str | None = None,
        photo_url: str | None = None,
        photo_file_id: str | None = None,
        video_url: str | None = None,
        video_file_id: str | None = None,
        document: str | InputFile | None = None,
        anti_flood: bool = True,
    ) -> bool:
        sender = EdelyaBotSender(
            user=self,
            text=text,
            kb=kb,
            parse_mode=parse_mode,
            photo_url=photo_url,
            photo_file_id=photo_file_id,
            video_url=video_url,
            video_file_id=video_file_id,
            document=document,
            anti_flood=anti_flood,
        )
        return sender()
