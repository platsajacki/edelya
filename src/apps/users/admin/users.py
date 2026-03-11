from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.users.models import User
from core.admin import admin


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        (
            'Credentials',
            {
                'fields': ('username', 'password'),
            },
        ),
        (
            'Telegram',
            {
                'fields': ('telegram_id', 'telegram_name', 'telegram_username'),
            },
        ),
        (
            'Permissions',
            {
                'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            },
        ),
        (
            'Advanced',
            {
                'classes': ('collapse',),
                'fields': ('id', 'last_login', 'date_joined', 'created_at', 'updated_at'),
            },
        ),
    )
    add_fieldsets = (
        (
            'Credentials',
            {
                'classes': ('wide',),
                'fields': ('username', 'password1', 'password2'),
            },
        ),
        (
            'Telegram',
            {
                'fields': ('telegram_id', 'telegram_name', 'telegram_username'),
            },
        ),
    )
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_login', 'date_joined')
    list_display = ('id', 'username', 'telegram_id', 'telegram_username', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'is_superuser')
    search_fields = ('username', 'telegram_id', 'telegram_username')
    ordering = ('-created_at',)
