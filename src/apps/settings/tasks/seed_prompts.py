from django.conf import settings

import yaml

from apps.settings.models import Prompt
from core import celery_app
from core.base.services import TaskService
from core.logging_handlers import loki_logger

PROMPTS_YAML_PATH = settings.BASE_DIR / 'data' / 'prompts.yaml'


class SeedPromptsService(TaskService):
    def _load_yaml_prompts(self) -> list[dict]:
        with open(PROMPTS_YAML_PATH, encoding='utf-8') as file:
            data = yaml.safe_load(file)
        return data.get('prompts', [])

    def act(self) -> int:
        prompts = self._load_yaml_prompts()
        created_count = 0
        for item in prompts:
            _, created = Prompt.objects.get_or_create(
                name=item['name'],
                defaults={
                    'text': item['text'],
                    'required_variables': item.get('required_variables', []),
                },
            )
            if created:
                loki_logger.info(self.get_log_msg(f'Created prompt {item["name"]!r}.'))
                created_count += 1
        return created_count


@celery_app.task
def task_seed_prompts() -> str:
    """
    Создаёт промпты из prompts.yaml, если они ещё не существуют.
    """
    service = SeedPromptsService()
    count = service()
    return service.get_log_msg(f'Created {count} prompt(s).')
