from django.conf import settings

import yaml

from apps.marketing.models.template_messages import MessageTemplate
from core import celery_app
from core.base.services import TaskService
from core.logging_handlers import loki_logger

TEMPLATES_YAML_PATH = settings.BASE_DIR / 'data' / 'message_templates.yaml'


class SeedMessageTemplatesService(TaskService):
    def _load_yaml_templates(self) -> list[dict]:
        with open(TEMPLATES_YAML_PATH, encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data.get('message_templates', [])

    def act(self) -> int:
        templates = self._load_yaml_templates()
        created_count = 0
        for item in templates:
            _, created = MessageTemplate.objects.get_or_create(
                name=item['name'],
                defaults={
                    'text_str': item['text_str'],
                    'with_variables': item.get('with_variables', False),
                    'variables_description': item.get('variables_description', ''),
                },
            )
            if created:
                loki_logger.info(self.get_log_msg(f'Created message template {item["name"]!r}.'))
                created_count += 1
        return created_count


@celery_app.task
def seed_message_templates() -> str:
    """
    Создаёт шаблоны сообщений из message_templates.yaml, если они ещё не существуют.
    """
    service = SeedMessageTemplatesService()
    count = service()
    return service.get_log_msg(f'Created {count} message template(s).')
