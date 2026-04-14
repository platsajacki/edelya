from django.contrib.admin import ModelAdmin

from apps.subscriptions.models.subscriptions import Subscription
from core.admin import admin


@admin.register(Subscription)
class SubscriptionAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('user', 'tariff', 'pending_tariff', 'status', 'auto_renew', 'payment_method'),
            },
        ),
        (
            'Trial',
            {
                'fields': ('trial_started_at', 'days_in_trial', 'trial_ended_at'),
            },
        ),
        (
            'Billing Period',
            {
                'fields': ('current_period_start', 'current_period_end'),
            },
        ),
        (
            'Cancellation',
            {
                'fields': ('cancelled_at',),
            },
        ),
        (
            'Advanced',
            {
                'classes': ('collapse',),
                'fields': ('id', 'created_at', 'updated_at'),
            },
        ),
    )
    readonly_fields = ('id', 'created_at', 'updated_at')
    list_display = ('id', 'user', 'tariff', 'status', 'auto_renew', 'trial_started_at', 'current_period_end')
    list_filter = ('status', 'auto_renew', 'tariff')
    search_fields = ('user__username', 'user__telegram_username', 'user__telegram_id')
    ordering = ('-created_at',)
    autocomplete_fields = ('user', 'tariff', 'pending_tariff', 'payment_method')
