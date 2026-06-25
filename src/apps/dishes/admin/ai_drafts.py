from django.contrib.admin import ModelAdmin

from apps.dishes.models.ai_drafts import DishAIDraft
from core.admin import admin


@admin.register(DishAIDraft)
class DishAIDraftAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('owner', 'status', 'created_dish'),
            },
        ),
        (
            'Recipe',
            {
                'fields': ('source_text', 'payload'),
            },
        ),
        (
            'AI',
            {
                'fields': ('ai_raw_response', 'validation_errors', 'usage'),
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
    list_display = ('id', 'owner', 'status', 'created_dish', 'created_at')
    list_filter = ('status',)
    list_select_related = ('owner', 'created_dish')
    search_fields = (
        'owner__username',
        'owner__telegram_username',
        'source_text',
        'created_dish__name',
    )
    ordering = ('-created_at',)
    autocomplete_fields = ('owner', 'created_dish')
