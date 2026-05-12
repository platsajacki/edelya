from django.conf import settings

import yaml

from apps.marketing.models.model_enums import MessageTemplateName
from core import celery_app
from core.base.services import TaskService
from core.logging_handlers import loki_logger, tg_logger

TEMPLATES_YAML_PATH = settings.BASE_DIR / 'data' / 'message_templates.yaml'


class ValidateMessageTemplatesService(TaskService):
    def _load_yaml_names(self) -> set[str]:
        with open(TEMPLATES_YAML_PATH, encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return {item['name'] for item in data.get('message_templates', [])}

    def act(self) -> list[str]:
        yaml_names = self._load_yaml_names()
        enum_values = set(MessageTemplateName.values)
        missing_in_yaml = enum_values - yaml_names
        missing_in_enum = yaml_names - enum_values
        issues = []
        for name in sorted(missing_in_yaml):
            issues.append(f'In enum but missing in YAML: {name!r}')
            loki_logger.warning(self.get_log_msg(f'Template {name!r} is defined in enum but missing in YAML.'))
        for name in sorted(missing_in_enum):
            issues.append(f'In YAML but missing in enum: {name!r}')
            loki_logger.warning(self.get_log_msg(f'Template {name!r} is defined in YAML but missing in enum.'))
        return issues


@celery_app.task
def validate_message_templates() -> str:
    """
    Проверяет, что все значения MessageTemplateName присутствуют в message_templates.yaml и наоборот.
    """
    service = ValidateMessageTemplatesService()
    issues = service()
    if issues:
        log = service.get_log_msg(f'Validation failed with {len(issues)} issue(s): {issues}')
        tg_logger.warning(log)
        return log
    return service.get_log_msg('All message template names are in sync.')
