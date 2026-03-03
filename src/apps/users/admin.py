from django.contrib.admin import ModelAdmin

from apps.users.models import User
from core.admin import admin


@admin.register(User)
class UserAdmin(ModelAdmin):
    list_display = (
        'id',
        'username',
        'telegram_id',
        'telegram_username',
        'is_staff',
        'is_active',
    )
    search_fields = (
        'username',
        'telegram_id',
        'telegram_username',
    )
    list_filter = ('is_staff', 'is_active')
