from django_celery_beat.models import IntervalSchedule, PeriodicTask

from apps.dishes.tasks.ai_draft_processor import process_ai_drafts_background
from apps.settings.tasks.setup import SetupPeriodicTasksService


class TestSetupPeriodicTasksService:
    def test_creates_ai_draft_background_task(self) -> None:
        SetupPeriodicTasksService()()
        task = PeriodicTask.objects.get(name='Фоновая обработка AI-черновиков блюд')
        assert task.task == process_ai_drafts_background.name
        assert task.interval.every == 2
        assert task.interval.period == IntervalSchedule.MINUTES
        assert task.enabled is True

    def test_updates_existing_ai_draft_background_task(self) -> None:
        interval = IntervalSchedule.objects.create(every=1, period=IntervalSchedule.HOURS)
        PeriodicTask.objects.create(
            name='Фоновая обработка AI-черновиков блюд',
            task='outdated.task',
            interval=interval,
            enabled=False,
        )
        SetupPeriodicTasksService()()
        task = PeriodicTask.objects.get(name='Фоновая обработка AI-черновиков блюд')
        assert task.task == process_ai_drafts_background.name
        assert task.interval.every == 2
        assert task.interval.period == IntervalSchedule.MINUTES
        assert task.enabled is True
