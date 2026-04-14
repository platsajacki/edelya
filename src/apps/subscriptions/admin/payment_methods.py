from django.contrib.admin import ModelAdmin

from apps.subscriptions.models.payment_methods import PaymentMethod
from core.admin import admin


@admin.register(PaymentMethod)
class PaymentMethodAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('id', 'user', 'payment_method_type', 'is_active'),
            },
        ),
        (
            'Card Info',
            {
                'fields': ('card_type', 'card_last4', 'title'),
            },
        ),
        (
            'YooKassa',
            {
                'fields': ('yookassa_payment_method_id',),
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
    readonly_fields = ('id', 'created_at', 'updated_at')
    list_display = ('id', 'user', 'payment_method_type', 'card_type', 'card_last4', 'title', 'is_active')
    list_filter = ('payment_method_type', 'is_active')
    search_fields = ('user__username', 'user__telegram_username', 'yookassa_payment_method_id', 'card_last4')
    ordering = ('-created_at',)
    autocomplete_fields = ('user',)
