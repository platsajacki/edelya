from django.contrib.admin import ModelAdmin, TabularInline

from apps.shopping.models.shopping_list import ShoppingList, ShoppingListItem
from core.admin import admin


class ShoppingListItemInline(TabularInline):
    model = ShoppingListItem
    fields = (
        'ingredient',
        'amount',
        'manual_amount',
        'is_checked',
        'is_manual',
        'position',
    )
    extra = 1
    ordering = ('position',)


@admin.register(ShoppingList)
class ShoppingListAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': (
                    'owner',
                    'name',
                    'date_from',
                    'date_to',
                )
            },
        ),
        (
            'Advanced',
            {
                'classes': ('collapse',),
                'fields': (
                    'id',
                    'created_at',
                    'updated_at',
                ),
            },
        ),
    )
    inlines = [ShoppingListItemInline]
    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
    )
    list_display = (
        'id',
        'name',
        'owner',
        'date_from',
        'date_to',
    )
    list_filter = (
        'date_from',
        'date_to',
    )
    search_fields = (
        'name',
        'owner__username',
        'owner__telegram_username',
    )
    ordering = ('-created_at',)
    autocomplete_fields = ('owner',)
    date_hierarchy = 'date_from'


@admin.register(ShoppingListItem)
class ShoppingListItemAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': (
                    'shopping_list',
                    'ingredient',
                    'amount',
                    'manual_amount',
                    'position',
                )
            },
        ),
        (
            'Status',
            {
                'fields': (
                    'is_checked',
                    'checked_at',
                    'is_manual',
                )
            },
        ),
        (
            'Advanced',
            {
                'classes': ('collapse',),
                'fields': (
                    'id',
                    'created_at',
                    'updated_at',
                ),
            },
        ),
    )
    readonly_fields = ('id', 'created_at', 'updated_at')
    list_display = (
        'id',
        'shopping_list',
        'ingredient',
        'amount',
        'is_checked',
        'is_manual',
        'position',
    )
    list_filter = (
        'is_checked',
        'is_manual',
    )
    search_fields = (
        'shopping_list__name',
        'ingredient__name',
    )
    ordering = ('position', '-created_at')
    autocomplete_fields = (
        'shopping_list',
        'ingredient',
    )
