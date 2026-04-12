from django.contrib.admin import ModelAdmin

from apps.subscriptions.models.tariffs import Tariff
from core.admin import admin


@admin.register(Tariff)
class TariffAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('published', 'name', 'price', 'billing_period', 'soon', 'is_active', 'sort_order'),
            },
        ),
        (
            'Description',
            {
                'fields': ('description',),
            },
        ),
        (
            'Features',
            {
                'fields': ('can_use_base_features', 'can_create_ai_recipes', 'is_trial_tariff', 'trial_days'),
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
    list_display = (
        'id',
        'name',
        'price',
        'billing_period',
        'is_active',
        'is_trial_tariff',
        'sort_order',
    )
    list_filter = ('is_active', 'billing_period')
    search_fields = ('name',)
    ordering = ('sort_order', 'price')
