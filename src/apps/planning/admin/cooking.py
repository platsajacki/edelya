from django.contrib.admin import ModelAdmin

from apps.planning.models.cooking import CookingEvent
from core.admin import admin


@admin.register(CookingEvent)
class CookingEventAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('owner', 'dish', 'cooking_date', 'position'),
            },
        ),
        (
            'Details',
            {
                'fields': ('notes',),
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
    list_display = ('id', 'owner', 'dish', 'cooking_date')
    list_filter = ('cooking_date',)
    search_fields = ('owner__username', 'owner__telegram_username', 'dish__name')
    ordering = ('-cooking_date',)
    autocomplete_fields = ('owner', 'dish')
    date_hierarchy = 'cooking_date'
