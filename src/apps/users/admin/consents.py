from django.contrib.admin import ModelAdmin

from apps.users.models.consents import ConsentLog
from core.admin import admin


@admin.register(ConsentLog)
class ConsentLogAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('user', 'consent_type', 'action'),
            },
        ),
        (
            'Context',
            {
                'fields': ('ip_address', 'user_agent', 'metadata'),
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
    list_display = ('id', 'user', 'consent_type', 'action', 'ip_address', 'created_at')
    list_filter = ('consent_type', 'action')
    search_fields = ('user__username', 'user__telegram_username', 'user__telegram_id')
    ordering = ('-created_at',)
    autocomplete_fields = ('user',)
