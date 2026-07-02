import unittest
from datetime import date

from payday.bank_holidays import (
    ENGLAND_WALES_2026_27,
    weekdays_in_range,
    working_days_in_range,
)


class TestHolidayData(unittest.TestCase):
    def test_nine_holidays_in_tax_year(self):
        self.assertEqual(len(ENGLAND_WALES_2026_27), 9)

    def test_all_holidays_are_weekdays(self):
        for d in ENGLAND_WALES_2026_27:
            self.assertLessEqual(d.weekday(), 4, f"{d} is a weekend")

    def test_no_duplicates(self):
        self.assertEqual(len(ENGLAND_WALES_2026_27), len(set(ENGLAND_WALES_2026_27)))

    def test_holidays_in_tax_year_range(self):
        start = date(2026, 4, 6)
        end = date(2027, 4, 5)
        for d in ENGLAND_WALES_2026_27:
            self.assertGreaterEqual(d, start)
            self.assertLessEqual(d, end)

    def test_easter_monday_2026_present(self):
        self.assertIn(date(2026, 4, 6), ENGLAND_WALES_2026_27)

    def test_good_friday_2027_present(self):
        self.assertIn(date(2027, 3, 26), ENGLAND_WALES_2026_27)

    def test_easter_monday_2027_present(self):
        self.assertIn(date(2027, 3, 29), ENGLAND_WALES_2026_27)

    def test_christmas_and_substitute_boxing_day(self):
        self.assertIn(date(2026, 12, 25), ENGLAND_WALES_2026_27)
        self.assertIn(date(2026, 12, 28), ENGLAND_WALES_2026_27)


class TestWeekdaysInRange(unittest.TestCase):
    def test_one_week(self):
        start = date(2026, 4, 6)
        end = date(2026, 4, 12)
        self.assertEqual(weekdays_in_range(start, end), 5)

    def test_full_tax_year(self):
        start = date(2026, 4, 6)
        end = date(2027, 4, 5)
        self.assertEqual(weekdays_in_range(start, end), 261)

    def test_august_december(self):
        start = date(2026, 8, 1)
        end = date(2026, 12, 31)
        self.assertEqual(weekdays_in_range(start, end), 109)

    def test_single_weekday(self):
        self.assertEqual(weekdays_in_range(date(2026, 4, 6), date(2026, 4, 6)), 1)

    def test_single_saturday(self):
        self.assertEqual(weekdays_in_range(date(2026, 4, 11), date(2026, 4, 11)), 0)


class TestWorkingDaysInRange(unittest.TestCase):
    def test_no_holidays(self):
        start = date(2026, 4, 6)
        end = date(2026, 4, 12)
        self.assertEqual(working_days_in_range(start, end, set()), 5)

    def test_one_holiday_on_weekday(self):
        start = date(2026, 5, 1)
        end = date(2026, 5, 10)
        holidays = {date(2026, 5, 4)}
        self.assertEqual(working_days_in_range(start, end, holidays), 5)

    def test_holiday_on_weekend_ignored(self):
        start = date(2026, 5, 1)
        end = date(2026, 5, 10)
        holidays = {date(2026, 5, 9)}
        self.assertEqual(working_days_in_range(start, end, holidays), 6)

    def test_full_tax_year_with_all_holidays(self):
        start = date(2026, 4, 6)
        end = date(2027, 4, 5)
        holidays = set(ENGLAND_WALES_2026_27)
        self.assertEqual(working_days_in_range(start, end, holidays), 252)

    def test_all_holidays_outside_range(self):
        start = date(2026, 6, 1)
        end = date(2026, 8, 1)
        holidays = {date(2026, 4, 6), date(2026, 12, 25)}
        self.assertEqual(working_days_in_range(start, end, holidays), 45)

    def test_zero_day_range(self):
        d = date(2026, 4, 12)
        self.assertEqual(working_days_in_range(d, d, set()), 0)
