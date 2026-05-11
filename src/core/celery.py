import os
from logging import Logger, getLogger
from typing import Any

from celery import Celery, signals

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

celery_app = Celery('core')
celery_app.config_from_object('django.conf:settings')
celery_app.autodiscover_tasks()


@signals.setup_logging.connect
def setup_celery_logging(**kwargs: Any) -> Logger:
    return getLogger('celery')


@signals.worker_ready.connect
def on_worker_ready(**kwargs: Any) -> None:
    from apps.subscriptions.tasks.setup import setup_periodic_tasks

    setup_periodic_tasks.delay()
