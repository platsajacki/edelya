from django.contrib.admin import ModelAdmin

from apps.marketing.models.template_messages import MessageTemplate
from core.admin import admin


@admin.register(MessageTemplate)
class MessageTemplateAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('name', 'with_variables'),
            },
        ),
        (
            'Content',
            {
                'fields': ('text_str',),
            },
        ),
        (
            'Variables',
            {
                'fields': ('variables_description',),
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
    list_display = ('id', 'name', 'with_variables', 'created_at')
    list_filter = ('with_variables',)
    search_fields = ('name',)
    ordering = ('name',)
