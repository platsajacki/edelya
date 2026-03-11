from django.contrib.admin import ModelAdmin

from apps.planning.models.meal_plan import MealPlanItem
from core.admin import admin


@admin.register(MealPlanItem)
class MealPlanItemAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('owner', 'date', 'dish', 'position', 'is_manual'),
            },
        ),
        (
            'Source',
            {
                'fields': ('cooking_event',),
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
    list_display = ('id', 'owner', 'date', 'dish', 'position', 'is_manual')
    list_filter = ('is_manual', 'date')
    search_fields = ('owner__username', 'owner__telegram_username', 'dish__name')
    ordering = ('-date', 'position')
    autocomplete_fields = ('owner', 'dish', 'cooking_event')
    date_hierarchy = 'date'
