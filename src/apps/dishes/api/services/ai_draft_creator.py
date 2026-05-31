from dataclasses import dataclass

from apps.dishes.models import DishAIDraft
from apps.dishes.tasks.ai_draft_processor import process_ai_draft
from core.base.services import BaseViewSetPerformService


@dataclass
class AIDraftCreator(BaseViewSetPerformService):
    def act(self) -> DishAIDraft:
        draft = self.serializer.save()
        process_ai_draft.delay(str(draft.id))
        return draft
