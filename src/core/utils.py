from datetime import date, timedelta
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules
from random import choice
from types import ModuleType

from django.core.cache import cache
from django.db.models import Q
from rest_framework.request import Request

from redis.backoff import EqualJitterBackoff
from redis.retry import Retry

from core.constants import DEFAULT_COLORS


def import_modules_from_package_dir(
    package_name: str,
    package_dir: str | Path,
    ignore_private: bool = True,
) -> list[ModuleType]:
    package_dir = Path(package_dir)
    imported_modules: list[ModuleType] = []
    for module_info in iter_modules([str(package_dir)]):
        module_name = module_info.name
        if ignore_private and module_name.startswith('_'):
            continue
        full_module_name = f'{package_name}.{module_name}'
        module = import_module(full_module_name)
        imported_modules.append(module)
    return imported_modules


def normalize_string(s: str) -> str:
    """Delete extra spaces and trim string."""
    s = s.strip()
    while '  ' in s:
        s = s.replace('  ', ' ')
    return s


def get_random_color(existing_colors: list | None = None) -> str:
    if existing_colors is None:
        return choice(DEFAULT_COLORS)
    set_of_available_colors = set(DEFAULT_COLORS) - set(existing_colors)
    if not set_of_available_colors:
        return choice(DEFAULT_COLORS)
    return choice(list(set_of_available_colors))


def build_weeks_q(dates: list[date], date_field: str = 'date') -> Q:
    weeks_q = Q()
    seen_weeks = set()
    for day in dates:
        week_start = day - timedelta(days=day.weekday())
        if week_start in seen_weeks:
            continue
        seen_weeks.add(week_start)
        week_end = week_start + timedelta(days=6)
        weeks_q |= Q(**{f'{date_field}__range': (week_start, week_end)})
    return weeks_q


def build_redis_retry_policy(attempts: int, base: float, cap: float) -> Retry:
    if attempts < 2:
        raise ValueError('attempts must be at least 2 to build a retry policy')
    if base < 0:
        raise ValueError('base must be non-negative')
    if cap < 0:
        raise ValueError('cap must be non-negative')
    backoff = EqualJitterBackoff(cap=cap, base=base)
    return Retry(backoff=backoff, retries=attempts)


def get_client_ip(request: Request) -> str | None:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class PaymentSyncFlagControler:
    _PAYMENT_SYNC_FLAG_KEY = 'payment:sync_processed:{}'
    _PAYMENT_SYNC_FLAG_TTL = 7 * 24 * 3600  # 1 week

    def set_payment_sync_flag(self, idempotence_key: str) -> None:
        cache.set(self._PAYMENT_SYNC_FLAG_KEY.format(idempotence_key), True, self._PAYMENT_SYNC_FLAG_TTL)

    def check_payment_sync_flag(self, idempotence_key: str) -> bool:
        return bool(cache.get(self._PAYMENT_SYNC_FLAG_KEY.format(idempotence_key)))


payment_sync_flag_controler: PaymentSyncFlagControler = PaymentSyncFlagControler()
