from datetime import date, timedelta
from random import choice

from django.db.models import Q

from core.constants import DEFAULT_COLORS


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


def build_weeks_q(dates: list[date]) -> Q:
    weeks_q = Q()
    seen_weeks = set()
    for day in dates:
        week_start = day - timedelta(days=day.weekday())
        if week_start in seen_weeks:
            continue
        seen_weeks.add(week_start)
        week_end = week_start + timedelta(days=6)
        weeks_q |= Q(date__range=(week_start, week_end))
    return weeks_q
