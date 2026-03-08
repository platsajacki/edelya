from datetime import date


def get_week_days(year: int, week: int) -> list[date]:
    return [date.fromisocalendar(year, week, day) for day in range(1, 8)]
