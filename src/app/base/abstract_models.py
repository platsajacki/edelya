from uuid import uuid4

from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    id = models.UUIDField(
        verbose_name='ID',
        primary_key=True,
        default=uuid4,
        editable=False,
    )
    created_at = models.DateTimeField(
        verbose_name='Created At',
        default=timezone.now,
        editable=False,
    )
    updated_at = models.DateTimeField(
        verbose_name='Updated At',
        auto_now=True,
    )

    class Meta:
        abstract = True


class BaseActiveModel(BaseModel):
    is_active = models.BooleanField(
        verbose_name='Активно',
        default=True,
    )

    class Meta:
        abstract = True

    def deactivate(self) -> None:
        self.is_active = False
        self.save(update_fields=['is_active'])
