from django.contrib.admin import ModelAdmin

from app.admin import admin
from users.models import User


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
