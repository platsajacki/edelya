from django.contrib.admin import ModelAdmin

from apps.marketing.models.notifications import Notification
from core.admin import admin


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('user', 'template', 'delivered', 'delivered_at'),
            },
        ),
        (
            'Content',
            {
                'fields': ('text_str',),
            },
        ),
        (
            'Error',
            {
                'fields': ('error_message',),
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
    readonly_fields = (
        'id',
        'user',
        'template',
        'delivered',
        'delivered_at',
        'text_str',
        'error_message',
        'created_at',
        'updated_at',
    )
    list_display = ('id', 'user', 'template', 'delivered', 'delivered_at', 'created_at')
    list_filter = ('delivered', 'template')
    list_select_related = ('user', 'template')
    search_fields = ('user__username', 'user__telegram_username', 'user__telegram_id')
    ordering = ('-created_at',)
