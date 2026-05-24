import json
from dataclasses import dataclass

from django.conf import settings

from apps.marketing.models.model_enums import MessageTemplateName
from apps.marketing.services.sender import NotificationSender
from apps.subscriptions.models.payments import Payment
from core.backends.redis_client import cluster_redis
from core.base.services import BaseService
from core.logging_handlers import loki_logger, tg_logger


@dataclass
class Tax3rCheckProcessor(BaseService):
    def _get_queue_key(self) -> str:
        return f'taxer:check_result:{settings.SERVICE_NAME}'

    def _raw_to_data(self, raw: str | bytes) -> dict | None:
        try:
            raw_str = raw.decode() if isinstance(raw, bytes) else raw
            data = json.loads(raw_str)
        except json.JSONDecodeError, ValueError:
            loki_logger.error(self.get_log_msg(f'Failed to parse Redis entry: {raw!r}'))
            return None
        if not isinstance(data, dict):
            loki_logger.error(self.get_log_msg(f'Parsed value is not a dict: {data!r}'))
            return None
        return data

    def _is_successful(self, data: dict) -> bool:
        if not data.get('success'):
            loki_logger.warning(self.get_log_msg(f'Unsuccessful check entry: {data}'))
            return False
        return True

    def _get_link(self, data: dict) -> str | None:
        link = data.get('link')
        if not link:
            loki_logger.warning(self.get_log_msg(f'No link in check entry: {data}'))
            return None
        return link

    def _get_item_id(self, data: dict) -> str | None:
        item_id = data.get('item_id')
        if not item_id:
            loki_logger.error(self.get_log_msg(f'Missing item_id in check entry: {data}'))
            return None
        return str(item_id)

    def _get_payment_by_id(self, item_id: str) -> Payment | None:
        payment = Payment.objects.to_send_check().filter(pk=item_id).first()
        if not payment:
            loki_logger.error(self.get_log_msg(f'Payment not found for item_id={item_id!r}'))
            return None
        return payment

    def _send_notification(self, payment: Payment) -> None:
        try:
            NotificationSender(
                user=payment.user,
                template_name=MessageTemplateName.SUBSCRIPTION_CHECK_FOR_CLIENT,
                variables={
                    'tariff_name': payment.subscription.tariff.name,
                    'check_url': payment.check_url,
                },
            )()
        except Exception as e:
            tg_logger.error(
                self.get_log_msg(f'Failed to send check notification for payment {payment.pk}: {e}'),
                exc_info=True,
            )

    def _process_entry(self, raw: str | bytes) -> None:
        data = self._raw_to_data(raw)
        if data is None:
            return
        if not self._is_successful(data):
            return
        link = self._get_link(data)
        if link is None:
            return
        item_id = self._get_item_id(data)
        if item_id is None:
            return
        payment = self._get_payment_by_id(item_id)
        if payment is None:
            return
        payment.is_check_sent = True
        payment.check_url = link
        payment.save(update_fields=['is_check_sent', 'check_url'])
        loki_logger.info(self.get_log_msg(f'Check saved for payment {payment.pk}, url={link!r}'))
        self._send_notification(payment)

    def act(self) -> int:
        queue_key = self._get_queue_key()
        counter = 0
        while (raw := cluster_redis.lpop(queue_key)) is not None:
            if not isinstance(raw, str | bytes):
                loki_logger.error(self.get_log_msg(f'Unexpected type for Redis entry: {type(raw)}, value: {raw!r}'))
                continue
            self._process_entry(raw=raw)
            counter += 1
        return counter
