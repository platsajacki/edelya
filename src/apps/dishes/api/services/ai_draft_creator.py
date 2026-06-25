from dataclasses import dataclass

from django.db import transaction

from apps.dishes.models import DishAIDraft
from apps.dishes.tasks.ai_draft_processor import process_ai_draft
from core.base.services import BaseViewSetPerformService


@dataclass
class AIDraftCreator(BaseViewSetPerformService):
    @transaction.atomic
    def act(self) -> DishAIDraft:
        draft = self.serializer.save()
        transaction.on_commit(lambda: process_ai_draft.delay(str(draft.id)))
        return draft
