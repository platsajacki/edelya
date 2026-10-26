import os
from logging import Logger, getLogger
from pathlib import Path
from typing import Any

from celery import Celery, signals

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

celery_app = Celery('core')
celery_app.config_from_object('django.conf:settings', namespace='CELERY')
celery_app.autodiscover_tasks()


class BeatLiveness:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._enabled = False

    def enable(self) -> None:
        self._enabled = True
        self.touch()

    def touch(self) -> None:
        if self._enabled:
            self._path.touch()


beat_liveness = BeatLiveness(Path('/tmp/beat-liveness'))


@signals.setup_logging.connect
def setup_celery_logging(**kwargs: Any) -> Logger:
    return getLogger('celery')


@signals.worker_ready.connect
def on_worker_ready(**kwargs: Any) -> None:
    from apps.marketing.tasks.seed_templates import seed_message_templates
    from apps.marketing.tasks.validate_templates import validate_message_templates
    from apps.settings.tasks.seed_prompts import task_seed_prompts
    from apps.settings.tasks.setup import setup_periodic_tasks

    validate_message_templates.delay()
    seed_message_templates.delay()
    task_seed_prompts.delay()
    setup_periodic_tasks.delay()


@signals.beat_init.connect
def enable_beat_liveness(**kwargs: Any) -> None:
    beat_liveness.enable()


@signals.after_task_publish.connect
def touch_beat_liveness(**kwargs: Any) -> None:
    beat_liveness.touch()
