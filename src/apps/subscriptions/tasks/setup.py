from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask

from apps.subscriptions.tasks.expire import (
    expire_cancelled_subscriptions,
    expire_past_due_subscriptions,
    expire_trials_without_payment,
)
from apps.subscriptions.tasks.past_due import process_past_due_charge
from apps.subscriptions.tasks.renewals import process_subscription_renewals
from apps.subscriptions.tasks.trials import process_trial_to_paid
from core import celery_app
from core.base.services import TaskService
from core.logging_handlers import loki_logger


class SetupPeriodicTasksService(TaskService):
    """
    Создаёт или обновляет периодические задачи в БД при старте воркера.
    Идемпотентна: повторный вызов не создаёт дубли — использует update_or_create.
    """

    def get_every_5_minutes_schedule(self) -> IntervalSchedule:
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=5,
            period=IntervalSchedule.MINUTES,
        )
        return schedule

    def get_crontab_schedule(self, hour: str, minute: str) -> CrontabSchedule:
        schedule, _ = CrontabSchedule.objects.get_or_create(
            hour=hour,
            minute=minute,
        )
        return schedule

    def get_task_definitions(self) -> list[dict]:
        every_5_minutes = self.get_every_5_minutes_schedule()
        daily_0300 = self.get_crontab_schedule(hour='3', minute='0')
        daily_0315 = self.get_crontab_schedule(hour='3', minute='15')
        daily_0330 = self.get_crontab_schedule(hour='3', minute='30')
        return [
            {
                'name': 'Конвертация триала в платную подписку',
                'task': process_trial_to_paid.name,
                'description': (
                    'Попытка 1: списание за 5 минут до окончания триала. При неуспехе подписка переходит в PAST_DUE.'
                ),
                'schedule': every_5_minutes,
                'schedule_field': 'interval',
            },
            {
                'name': 'Автопродление активных подписок',
                'task': process_subscription_renewals.name,
                'description': (
                    'Попытка 1: списание за 5 минут до окончания периода. При неуспехе подписка переходит в PAST_DUE.'
                ),
                'schedule': every_5_minutes,
                'schedule_field': 'interval',
            },
            {
                'name': 'Повторное списание для PAST_DUE подписок',
                'task': process_past_due_charge.name,
                'description': (
                    'Попытка 2 (последняя): списание за 5 минут до конца grace period. '
                    'При неуспехе подписка переходит в EXPIRED.'
                ),
                'schedule': every_5_minutes,
                'schedule_field': 'interval',
            },
            {
                'name': 'Истечение брошенных триалов',
                'task': expire_trials_without_payment.name,
                'description': (
                    'Ежедневно в 03:00. Переводит в EXPIRED Trial-подписки, '
                    'где pending_tariff = None (пользователь не выбрал план).'
                ),
                'schedule': daily_0300,
                'schedule_field': 'crontab',
            },
            {
                'name': 'Истечение PAST_DUE подписок после grace period',
                'task': expire_past_due_subscriptions.name,
                'description': (
                    'Ежедневно в 03:15. Страховочный fallback: '
                    'переводит в EXPIRED PAST_DUE-подписки, у которых истёк grace period.'
                ),
                'schedule': daily_0315,
                'schedule_field': 'crontab',
            },
            {
                'name': 'Истечение отменённых подписок',
                'task': expire_cancelled_subscriptions.name,
                'description': (
                    'Ежедневно в 03:30. Переводит в EXPIRED ACTIVE-подписки '
                    'с auto_renew=False и истёкшим current_period_end.'
                ),
                'schedule': daily_0330,
                'schedule_field': 'crontab',
            },
        ]

    def act(self) -> None:
        tasks = self.get_task_definitions()
        for task_def in tasks:
            schedule_field = task_def.pop('schedule_field')
            schedule = task_def.pop('schedule')
            defaults = {
                schedule_field: schedule,
                'task': task_def['task'],
                'description': task_def['description'],
                'enabled': True,
            }
            _, created = PeriodicTask.objects.update_or_create(
                name=task_def['name'],
                defaults=defaults,
            )
            action = 'Создана' if created else 'Обновлена'
            loki_logger.info(self.get_log_msg(f'{action} периодическая задача: {task_def["name"]!r}'))


@celery_app.task
def setup_periodic_tasks() -> str:
    """Создаёт или обновляет периодические задачи в БД. Вызывается при старте воркера."""
    SetupPeriodicTasksService()()
    return 'Periodic tasks set up successfully.'
