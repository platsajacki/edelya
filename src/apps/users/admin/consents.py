from django.contrib.admin import ModelAdmin

from apps.users.models.consents import ConsentLog
from apps.users.models.legal_docs import PrivacyPolicyVersion, TermsOfServiceVersion
from core.admin import admin


@admin.register(ConsentLog)
class ConsentLogAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('user', 'consent_type', 'action'),
            },
        ),
        (
            'Context',
            {
                'fields': ('ip_address', 'user_agent', 'metadata'),
            },
        ),
        (
            'Document Versions',
            {
                'fields': ('terms_of_service_version', 'privacy_policy_version'),
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
    list_display = ('id', 'user', 'consent_type', 'action', 'ip_address', 'created_at')
    list_filter = ('consent_type', 'action')
    list_select_related = ('user',)
    search_fields = ('user__username', 'user__telegram_username', 'user__telegram_id')
    ordering = ('-created_at',)
    autocomplete_fields = ('user',)


@admin.register(TermsOfServiceVersion)
class TermsOfServiceVersionAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('version', 'is_active', 'published_at'),
            },
        ),
        (
            'Content',
            {
                'fields': ('content',),
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
    list_display = ('id', 'version', 'is_active', 'published_at', 'created_at')
    list_filter = ('is_active',)
    ordering = ('-published_at',)


@admin.register(PrivacyPolicyVersion)
class PrivacyPolicyVersionAdmin(ModelAdmin):
    fieldsets = (
        (
            'General',
            {
                'fields': ('version', 'is_active', 'published_at'),
            },
        ),
        (
            'Content',
            {
                'fields': ('content',),
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
    list_display = ('id', 'version', 'is_active', 'published_at', 'created_at')
    list_filter = ('is_active',)
    ordering = ('-published_at',)
