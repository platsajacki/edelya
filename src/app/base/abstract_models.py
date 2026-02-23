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
