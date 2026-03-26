from django.contrib.admin import ModelAdmin, TabularInline

from apps.dishes.models.dishes import Dish, DishCategory, DishIngredient
from core.admin import admin


class DishIngredientInline(TabularInline):
    model = DishIngredient
    fields = ('ingredient', 'amount', 'is_optional', 'position')
    extra = 1
    ordering = ('position',)


@admin.register(DishCategory)
class DishCategoryAdmin(ModelAdmin):
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


@admin.register(Dish)
class DishAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('owner', 'category', 'name', 'is_active'),
            },
        ),
        (
            'Recipe',
            {
                'fields': ('recipe',),
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
    inlines = [DishIngredientInline]
    readonly_fields = ('id', 'created_at', 'updated_at')
    list_display = ('id', 'name', 'category', 'owner', 'is_active')
    list_filter = ('is_active', 'category')
    search_fields = ('name', 'owner__username', 'owner__telegram_username')
    ordering = ('name',)
    autocomplete_fields = ('owner', 'category')
