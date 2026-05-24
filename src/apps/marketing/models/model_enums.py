from django.db import models


class MessageTemplateName(models.TextChoices):
    SUBSCRIPTION_FIRST_PAYMENT_SUCCEEDED = (
        'subscription_first_payment_succeeded',
        'Первый платёж по подписке успешен',
    )
    SUBSCRIPTION_RECURRING_PAYMENT_SUCCEEDED = (
        'subscription_recurring_payment_succeeded',
        'Регулярный платёж по подписке успешен',
    )
    SUBSCRIPTION_PAYMENT_FAILED = (
        'subscription_payment_failed',
        'Платёж по подписке не прошёл',
    )
    SUBSCRIPTION_CARD_BOUND = (
        'subscription_card_bound',
        'Карта привязана',
    )
    SUBSCRIPTION_CARD_UNBOUND = (
        'subscription_card_unbound',
        'Карта отвязана',
    )
    SUBSCRIPTION_TARIFF_UPGRADED = (
        'subscription_tariff_upgraded',
        'Тариф повышен',
    )
    SUBSCRIPTION_TARIFF_DOWNGRADE_SCHEDULED = (
        'subscription_tariff_downgrade_scheduled',
        'Понижение тарифа запланировано',
    )
    SUBSCRIPTION_AUTO_RENEW_CANCELLED = (
        'subscription_auto_renew_cancelled',
        'Автопродление отключено',
    )
    SUBSCRIPTION_AUTO_RENEW_RESUMED = (
        'subscription_auto_renew_resumed',
        'Автопродление восстановлено',
    )
    SUBSCRIPTION_EXPIRED = (
        'subscription_expired',
        'Подписка истекла',
    )
    SUBSCRIPTION_TRIAL_EXPIRED = (
        'subscription_trial_expired',
        'Пробный период истёк',
    )
    SUBSCRIPTION_CANCELLED_EXPIRED = (
        'subscription_cancelled_expired',
        'Оплаченный период завершился',
    )
    SUBSCRIPTION_CHECK_FOR_CLIENT = (
        'subscription_check_for_client',
        'Чек для клиента',
    )
