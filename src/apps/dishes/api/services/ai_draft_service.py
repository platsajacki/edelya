from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import ClassVar

from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.dishes.models import DishAIDraft, DishAIDraftStatus
from core.base.services import BaseViewSetService


@dataclass
class AIDraftService(BaseViewSetService):
    draft: DishAIDraft = dc_field(kw_only=True)
    not_parsed_message: ClassVar[str] = 'AI draft must be parsed.'

    @transaction.atomic
    def __call__(self) -> Response:
        self.draft = DishAIDraft.objects.select_for_update().get(pk=self.draft.pk)
        return super().__call__()

    def validate_draft_status(self) -> None:
        if self.draft.status != DishAIDraftStatus.PARSED:
            raise ValidationError(self.not_parsed_message)

    def get_validators(self) -> list[Callable]:
        return super().get_validators() + [self.validate_draft_status]
