from django.contrib.admin import ModelAdmin, TabularInline
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.dishes.models.dishes import Dish, DishCategory, DishIngredient
from core.admin import admin


class DishIngredientInline(TabularInline):
    model = DishIngredient
    fields = (
        'ingredient',
        'ingredient_name',
        'ingredient_category',
        'ingredient_unit',
        'amount',
        'is_optional',
        'position',
    )
    readonly_fields = ('ingredient_name', 'ingredient_category', 'ingredient_unit')
    extra = 1
    ordering = ('position',)

    @admin.display(description='Ед. измерения')
    def ingredient_unit(self, obj: DishIngredient) -> str:
        return obj.ingredient.get_base_unit_display()

    @admin.display(description='Название ингредиента')
    def ingredient_name(self, obj: DishIngredient) -> str:
        return obj.ingredient.name

    @admin.display(description='Категория ингредиента')
    def ingredient_category(self, obj: DishIngredient) -> str:
        return obj.ingredient.category.name

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).select_related('ingredient', 'ingredient__category')


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

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).select_related('owner', 'category')
