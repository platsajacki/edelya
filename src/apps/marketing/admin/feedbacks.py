from django.contrib.admin import ModelAdmin

from apps.marketing.models.feedbacks import Feedback
from core.admin import admin


@admin.register(Feedback)
class FeedbackAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('id', 'user', 'rating'),
            },
        ),
        (
            'Content',
            {
                'fields': ('text',),
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
    readonly_fields = ('id', 'user', 'rating', 'text', 'created_at', 'updated_at')
    list_display = ('id', 'user', 'rating', 'created_at')
    list_filter = ('rating',)
    list_select_related = ('user',)
    search_fields = ('user__username', 'user__telegram_username', 'user__telegram_id', 'text')
    ordering = ('-created_at',)
