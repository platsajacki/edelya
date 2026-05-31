from django.contrib.admin import ModelAdmin

from apps.settings.models import Prompt
from core.admin import admin


@admin.register(Prompt)
class PromptAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('name',),
            },
        ),
        (
            'Content',
            {
                'fields': ('text', 'required_variables'),
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
    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)
