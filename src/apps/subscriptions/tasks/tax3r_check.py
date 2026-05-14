from apps.subscriptions.services.tax3r_check_processor import Tax3rCheckProcessor
from core import celery_app
from core.base.services import TaskService


class Tax3rCheckProcessorTaskService(TaskService):
    def act(self) -> int:
        return Tax3rCheckProcessor()()


@celery_app.task
def process_tax3r_check_results() -> str:
    """Читает результаты проверки от Tax3r из Redis-очереди и обновляет платежи."""
    service = Tax3rCheckProcessorTaskService()
    count = service()
    return service.get_log_msg(f'Processed {count} Tax3r check results.')
