from django.core.cache import cache


class PaymentSyncFlagControler:
    __instance = None
    _PAYMENT_SYNC_FLAG_KEY = 'payment:sync_processed:{}'
    _PAYMENT_SYNC_FLAG_TTL = 7 * 24 * 3600  # 1 week

    def __new__(cls) -> PaymentSyncFlagControler:
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def set_payment_sync_flag(self, idempotence_key: str) -> None:
        cache.set(self._PAYMENT_SYNC_FLAG_KEY.format(idempotence_key), True, self._PAYMENT_SYNC_FLAG_TTL)

    def check_payment_sync_flag(self, idempotence_key: str) -> bool:
        return bool(cache.get(self._PAYMENT_SYNC_FLAG_KEY.format(idempotence_key)))


payment_sync_flag_controler: PaymentSyncFlagControler = PaymentSyncFlagControler()
