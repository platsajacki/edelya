from django.contrib.admin import ModelAdmin

from apps.dishes.models.ingredients import Ingredient, IngredientCategory
from core.admin import admin


@admin.register(IngredientCategory)
class IngredientCategoryAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('name', 'is_active'),
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
    list_display = ('id', 'name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Ingredient)
class IngredientAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('owner', 'category', 'name', 'base_unit', 'is_active'),
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
    list_display = ('id', 'name', 'category', 'base_unit', 'owner', 'is_active')
    list_filter = ('is_active', 'base_unit', 'category')
    search_fields = ('name', 'owner__username', 'owner__telegram_username')
    ordering = ('name',)
    autocomplete_fields = ('owner', 'category')
