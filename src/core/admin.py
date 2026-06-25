from django.conf import settings
from django.contrib import admin, messages
from django.core.cache import InvalidCacheBackendError, caches
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path

name = 'Edelya'
admin.site.site_header = f'{name} Admin'
admin.site.site_title = f'{name} Admin'
admin.site.index_title = f'{name} Administration'
admin.site.index_template = 'admin/custom_index.html'


def _clear_cache_view(request: HttpRequest, cache_alias: str, cache_name: str) -> HttpResponse:
    if request.method == 'POST':
        try:
            caches[cache_alias].clear()
            messages.success(request, f'{cache_name} cache cleared successfully.')
        except InvalidCacheBackendError:
            messages.warning(request, f'{cache_name} cache backend is not configured (DEBUG mode?).')
        return HttpResponseRedirect('../')
    context = admin.site.each_context(request)
    context['cache_name'] = cache_name
    context['title'] = f'Clear {cache_name} Cache'
    return TemplateResponse(request, 'admin/clear_cache.html', context)


def _clear_api_cache_view(request: HttpRequest) -> HttpResponse:
    return _clear_cache_view(request, settings.API_CACHE_ALIAS, 'API')


def _clear_ai_cache_view(request: HttpRequest) -> HttpResponse:
    return _clear_cache_view(request, settings.AI_CACHE_ALIAS, 'AI')


_original_get_urls = admin.site.get_urls


def _patched_get_urls() -> list:
    custom_urls = [
        path('clear-api-cache/', admin.site.admin_view(_clear_api_cache_view), name='clear_api_cache'),
        path('clear-ai-cache/', admin.site.admin_view(_clear_ai_cache_view), name='clear_ai_cache'),
    ]
    return custom_urls + _original_get_urls()


admin.site.get_urls = _patched_get_urls  # type: ignore[method-assign]
