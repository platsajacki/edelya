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


def _clear_api_cache_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        try:
            caches[settings.API_CACHE_KEY_PREFIX].clear()
            messages.success(request, 'API cache cleared successfully.')
        except InvalidCacheBackendError:
            messages.warning(request, 'API cache backend is not configured (DEBUG mode?).')
        return HttpResponseRedirect('../')
    context = admin.site.each_context(request)
    context['title'] = 'Clear API Cache'
    return TemplateResponse(request, 'admin/clear_api_cache.html', context)


_original_get_urls = admin.site.get_urls


def _patched_get_urls() -> list:
    custom_urls = [
        path('clear-api-cache/', admin.site.admin_view(_clear_api_cache_view), name='clear_api_cache'),
    ]
    return custom_urls + _original_get_urls()


admin.site.get_urls = _patched_get_urls  # type: ignore[method-assign]
