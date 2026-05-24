from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import datetime

from django.utils import timezone

from apps.marketing.models.model_enums import MessageTemplateName
from apps.marketing.models.notifications import Notification
from apps.marketing.models.template_messages import MessageTemplate
from apps.users.models.users import User
from core.base.services import BaseService
from core.logging_handlers import loki_logger


def fmt_date(dt: datetime | None) -> str:
    return dt.strftime('%d.%m.%Y') if dt else '—'


@dataclass
class NotificationSender(BaseService):
    user: User
    template_name: MessageTemplateName
    variables: dict = dc_field(default_factory=dict)

    def create_notification(
        self, text: str, delivered: bool, template: MessageTemplate, error_message: str = ''
    ) -> None:
        Notification.objects.create(
            user=self.user,
            template=template,
            text_str=text,
            delivered=delivered,
            delivered_at=timezone.now() if delivered else None,
            error_message=error_message,
        )

    def send_notification(self) -> bool:
        template = MessageTemplate.objects.filter(name=self.template_name).first()
        if template is None:
            loki_logger.error(self.get_log_msg(f'MessageTemplate {self.template_name!r} not found, skipping.'))
            return False
        text = template.render_text_str(self.variables)
        delivered = self.user.send_telegram_message(text)
        error_message = '' if delivered else 'Failed to send Telegram message'
        self.create_notification(text=text, delivered=delivered, template=template, error_message=error_message)
        return delivered

    def act(self) -> bool:
        try:
            return self.send_notification()
        except Exception as e:
            loki_logger.error(
                self.get_log_msg(
                    f'Failed to send notification {self.template_name!r} to user {self.user.id}. Error: {e}'
                ),
                exc_info=True,
            )
            return False
