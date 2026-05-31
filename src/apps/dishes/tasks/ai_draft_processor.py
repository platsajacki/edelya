from dataclasses import dataclass

from core import celery_app
from core.base.services import TaskService


@dataclass
class AIDraftProcessor(TaskService):
    draft_id: str

    def act(self) -> str:
        return 'AI draft processed.'


@celery_app.task
def process_ai_draft(draft_id: str) -> str:
    """
    Задача для обработки AI-черновиков блюд.
    """
    service = AIDraftProcessor(draft_id=draft_id)
    return service()
