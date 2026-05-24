from decimal import Decimal
from typing import Any
from uuid import uuid4

from django.conf import settings

from yookassa import Configuration
from yookassa import Payment as YooPayment
from yookassa import PaymentMethod as YooPaymentMethod
from yookassa.payment import PaymentResponse
from yookassa.payment_method import PaymentMethodResponse

from core.logging_handlers import loki_logger


class YookassaPaymentsService:
    """Обёртка над YooKassa Python SDK для работы с платежами и способами оплаты.

    Используется как синглтон (`yookassa_service`) — конфигурируется один раз
    при старте приложения через `YOOKASSA_SHOP_ID` и `YOOKASSA_SECRET_KEY`.
    """

    _instance: YookassaPaymentsService

    def __new__(cls) -> YookassaPaymentsService:
        if not hasattr(cls, '_instance'):
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        Configuration.configure(
            account_id=settings.YOOKASSA_SHOP_ID,
            secret_key=settings.YOOKASSA_SECRET_KEY,
        )

    def create_payment(
        self,
        amount: Decimal,
        currency: str = 'RUB',
        description: str | None = None,
        return_url: str | None = None,
        save_payment_method: bool = False,
        payment_method_id: str | None = None,
        capture: bool = True,
        idempotence_key: str | None = None,
        metadata: dict | None = None,
    ) -> PaymentResponse:
        """Создание платежа — POST /v3/payments.

        Сценарии использования:
        - `save_payment_method=True` — первый платёж с сохранением карты для автоплатежей.
        - `payment_method_id` заполнен — рекуррентный автоплатёж без участия пользователя.
        - `capture=False` — платёж в две стадии: деньги холдируются, списание через `capture_payment()`.
        - По умолчанию — одностадийный платёж с редиректом на страницу YooKassa.
        """
        idempotence_key = idempotence_key or str(uuid4())
        params: dict[str, Any] = {
            'amount': {'value': str(amount), 'currency': currency},
            'capture': capture,
            'save_payment_method': save_payment_method,
        }
        if payment_method_id:
            params['payment_method_id'] = payment_method_id
        else:
            params['confirmation'] = {'type': 'redirect', 'return_url': return_url or settings.YOOKASSA_RETURN_URL}
        if description:
            params['description'] = description[:128]
        if metadata:
            params['metadata'] = metadata
        loki_logger.info('Creating YooKassa payment, idempotence_key=%s', idempotence_key)
        return YooPayment.create(params, idempotency_key=idempotence_key)

    def get_payment(self, payment_id: str) -> PaymentResponse:
        """Получение актуального состояния платежа — GET /v3/payments/{payment_id}.

        Используется для polling'а статуса или в webhook-обработчике.
        Жизненный цикл: pending → waiting_for_capture → succeeded / canceled.
        """
        loki_logger.info('Fetching YooKassa payment, payment_id=%s', payment_id)
        return YooPayment.find_one(payment_id)

    def capture_payment(
        self,
        payment_id: str,
        amount: Decimal | None = None,
        currency: str = 'RUB',
        idempotence_key: str | None = None,
    ) -> PaymentResponse:
        """Подтверждение (capture) холдированного платежа — POST /v3/payments/{id}/capture.

        Применяется при двустадийной оплате (`capture=False`): деньги авторизованы,
        но ещё не списаны. Можно передать `amount` меньше исходного для частичного списания.
        """
        idempotence_key = idempotence_key or str(uuid4())
        params: dict[str, Any] | None = None
        if amount is not None:
            params = {'amount': {'value': str(amount), 'currency': currency}}
        loki_logger.info('Capturing YooKassa payment, payment_id=%s', payment_id)
        return YooPayment.capture(payment_id, params, idempotency_key=idempotence_key)

    def cancel_payment(self, payment_id: str, idempotence_key: str | None = None) -> PaymentResponse:
        """Отмена холдированного платежа — POST /v3/payments/{id}/cancel.

        Работает только для статуса `waiting_for_capture`.
        Деньги разблокируются на карте пользователя.
        """
        idempotence_key = idempotence_key or str(uuid4())
        loki_logger.info('Cancelling YooKassa payment, payment_id=%s', payment_id)
        return YooPayment.cancel(payment_id, idempotency_key=idempotence_key)

    def create_payment_method_binding(
        self,
        idempotence_key: str | None = None,
        return_url: str | None = None,
    ) -> PaymentResponse:
        """Привязка карты без списания — POST /v3/payment_methods.

        Создаёт объект способа оплаты в YooKassa для последующих автоплатежей.
        В ответе приходит `confirmation_url` — редирект на страницу ввода карты.
        После подтверждения YooKassa отправляет webhook `payment_method.active`.
        Используется в сценарии «выбор тарифа во время триала».
        """
        idempotence_key = idempotence_key or str(uuid4())
        params: dict[str, Any] = {
            'type': 'bank_card',
            'confirmation': {
                'type': 'redirect',
                'return_url': return_url or settings.YOOKASSA_RETURN_URL,
            },
        }
        loki_logger.info('Creating YooKassa payment method binding, idempotence_key=%s', idempotence_key)
        return YooPaymentMethod.create(params, idempotency_key=idempotence_key)

    def get_payment_method(self, payment_method_id: str) -> PaymentMethodResponse:
        """Получение сохранённого способа оплаты — GET /v3/payment_methods/{id}.

        Используется для проверки статуса привязки (pending → active)
        и получения данных карты (last4, card_type) для отображения в ЛК.
        """
        loki_logger.info('Fetching YooKassa payment method, payment_method_id=%s', payment_method_id)
        return YooPaymentMethod.find_one(payment_method_id)


yookassa_service = YookassaPaymentsService()
