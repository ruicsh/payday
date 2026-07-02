"""England & Wales bank holidays for the 2026/27 tax year."""

from datetime import date, timedelta

ENGLAND_WALES_2026_27: list[date] = [
    date(2026, 4, 6),
    date(2026, 5, 4),
    date(2026, 5, 25),
    date(2026, 8, 31),
    date(2026, 12, 25),
    date(2026, 12, 28),
    date(2027, 1, 1),
    date(2027, 3, 26),
    date(2027, 3, 29),
]


def weekdays_in_range(start: date, end: date) -> int:
    days = (end - start).days + 1
    full_weeks = days // 7
    weekdays = full_weeks * 5
    remainder = days % 7
    current = start + timedelta(days=full_weeks * 7)
    for _ in range(remainder):
        if current.weekday() < 5:
            weekdays += 1
        current += timedelta(days=1)
    return weekdays


def working_days_in_range(start: date, end: date, holidays: set[date]) -> int:
    count = weekdays_in_range(start, end)
    for h in holidays:
        if start <= h <= end and h.weekday() < 5:
            count -= 1
    return count
