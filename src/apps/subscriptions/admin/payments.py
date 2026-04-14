from django.contrib.admin import ModelAdmin

from apps.subscriptions.models.payments import Payment
from core.admin import admin


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('id', 'idempotence_key', 'user', 'subscription', 'payment_type', 'status'),
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
                'fields': ('paid_at', 'description', 'cancellation_reason', 'metadata'),
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
    readonly_fields = ('id', 'idempotence_key', 'created_at', 'updated_at')
    list_display = ('id', 'user', 'subscription', 'payment_type', 'status', 'amount', 'currency', 'paid_at')
    list_filter = ('status', 'payment_type', 'currency')
    search_fields = ('user__username', 'user__telegram_username', 'yookassa_payment_id')
    ordering = ('-created_at',)
    autocomplete_fields = ('user', 'subscription', 'payment_method')
