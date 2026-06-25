from django import forms
from django.contrib.admin import ModelAdmin
from django.contrib.postgres.forms import SimpleArrayField

from apps.subscriptions.models.tariffs import Tariff
from core.admin import admin


class TariffAdminForm(forms.ModelForm):
    description_items = SimpleArrayField(
        base_field=forms.CharField(),
        delimiter='\n',
        required=False,
        widget=forms.Textarea(
            attrs={
                'rows': 8,
                'style': 'width: 600px;',
            }
        ),
        help_text='Каждый пункт с новой строки. Запятые внутри пункта использовать можно.',
    )

    class Meta:
        model = Tariff
        fields = '__all__'

    def clean_description_items(self) -> list[str]:
        description_items = self.cleaned_data.get('description_items') or []
        return [item.strip() for item in description_items if item and item.strip()]


@admin.register(Tariff)
class TariffAdmin(ModelAdmin):
    form = TariffAdminForm
    fieldsets = (
        (
            'General',
            {
                'fields': ('published', 'name', 'price', 'billing_period', 'soon', 'is_active', 'sort_order'),
            },
        ),
        (
            'Description',
            {
                'fields': ('description', 'description_items'),
            },
        ),
        (
            'Features',
            {
                'fields': ('can_use_base_features', 'can_create_ai_recipes', 'is_trial_tariff', 'trial_days'),
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
    list_display = (
        'id',
        'name',
        'price',
        'billing_period',
        'is_active',
        'is_trial_tariff',
        'sort_order',
    )
    list_filter = ('is_active', 'billing_period')
    search_fields = ('name',)
    ordering = ('sort_order', 'price')
