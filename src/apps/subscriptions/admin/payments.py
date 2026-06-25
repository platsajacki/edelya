from django.contrib.admin import ModelAdmin

from apps.subscriptions.models.payments import Payment
from core.admin import admin


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('id', 'idempotence_key', 'user', 'subscription', 'payment_type', 'status', 'send_to_tax3r'),
            },
        ),
        (
            'Amount',
            {
                'fields': ('amount', 'currency'),
            },
        ),
        (
            'Payment Method',
            {
                'fields': ('payment_method',),
            },
        ),
        (
            'YooKassa',
            {
                'fields': ('yookassa_payment_id',),
            },
        ),
        (
            'Details',
            {
                'fields': ('paid_at', 'description', 'cancellation_reason', 'metadata', 'is_check_sent', 'check_url'),
            },
        ),
        (
            'Advanced',
            {
                'classes': ('collapse',),
                'fields': ('created_at', 'updated_at'),
            },
        ),
    )
    readonly_fields = (
        'id',
        'idempotence_key',
        'user',
        'subscription',
        'payment_type',
        'status',
        'send_to_tax3r',
        'amount',
        'currency',
        'payment_method',
        'yookassa_payment_id',
        'paid_at',
        'description',
        'cancellation_reason',
        'metadata',
        'is_check_sent',
        'check_url',
        'created_at',
        'updated_at',
    )
    list_display = ('id', 'user', 'subscription', 'payment_type', 'status', 'amount', 'currency', 'paid_at')
    list_filter = ('status', 'payment_type', 'currency')
    list_select_related = ('user', 'subscription')
    search_fields = ('user__username', 'user__telegram_username', 'yookassa_payment_id')
    ordering = ('-created_at',)
