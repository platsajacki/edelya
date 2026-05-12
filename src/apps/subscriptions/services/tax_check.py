from dataclasses import dataclass

from django.conf import settings

from apps.subscriptions.models.payments import Payment
from core.base.services import BaseService
from core.external_requests.tax3r import TaxCheckData, send_payment_check_to_taxer
from core.logging_handlers import loki_logger, tg_logger


@dataclass
class TaxCheckSender(BaseService):
    payment: Payment
    service_name: str

    def send_to_tax_service(self, data: TaxCheckData) -> None:
        try:
            response = send_payment_check_to_taxer(data)
            response.raise_for_status()
            loki_logger.info(self.get_log_msg(f'Tax check sent for payment {self.payment.id!r}, data: {data}'))
        except Exception as e:
            tg_logger.error(
                self.get_log_msg(f'Failed to send tax check for payment {self.payment.id!r}: {e}'),
                exc_info=True,
            )

    def act(self) -> None:
        if not settings.SEND_CHECKS_TO_TAX3R:
            return
        if self.payment.amount <= 0:
            return
        data = TaxCheckData(
            service_name=self.service_name,
            price=str(self.payment.amount),
            payment_id=str(self.payment.id),
        )
        self.send_to_tax_service(data)
