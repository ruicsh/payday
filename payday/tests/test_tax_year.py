import unittest
from payday.tax_year import (
    contract_period_label,
    months_in_tax_year,
    pro_rate_contract,
    pro_rate_days,
)


class TestTaxYear(unittest.TestCase):
    def test_months_in_tax_year_august(self):
        # Aug → months 5-12 = 8 months
        self.assertEqual(months_in_tax_year(8), 8)

    def test_months_in_tax_year_april(self):
        # Apr → months 1-12 = full year
        self.assertEqual(months_in_tax_year(4), 12)

    def test_months_in_tax_year_march(self):
        # Mar → last month = 1 month
        self.assertEqual(months_in_tax_year(3), 1)

    def test_months_in_tax_year_january(self):
        # Jan → position 10, months 10-12 = 3 months
        self.assertEqual(months_in_tax_year(1), 3)

    def test_months_in_tax_year_december(self):
        # Dec → position 9, months 9-12 = 4 months
        self.assertEqual(months_in_tax_year(12), 4)

    def test_months_in_tax_year_may(self):
        # May → position 2, months 2-12 = 11 months
        self.assertEqual(months_in_tax_year(5), 11)

    def test_months_in_tax_year_july(self):
        # Jul → position 4, months 4-12 = 9 months
        self.assertEqual(months_in_tax_year(7), 9)

    def test_months_in_tax_year_invalid_low(self):
        with self.assertRaises(ValueError):
            months_in_tax_year(0)

    def test_months_in_tax_year_invalid_high(self):
        with self.assertRaises(ValueError):
            months_in_tax_year(13)

    def test_pro_rate_days_full_year(self):
        self.assertEqual(pro_rate_days(240, 12), 240)

    def test_pro_rate_days_eight_months(self):
        self.assertEqual(pro_rate_days(240, 8), 160)

    def test_pro_rate_days_three_months(self):
        self.assertEqual(pro_rate_days(240, 3), 60)

    def test_pro_rate_days_one_month(self):
        self.assertEqual(pro_rate_days(240, 1), 20)

    def test_pro_rate_days_rounding(self):
        # 250 * 8 / 12 = 166.67 → 167
        self.assertEqual(pro_rate_days(250, 8), 167)

    def test_contract_period_label_august(self):
        label = contract_period_label(8, 8)
        self.assertEqual(label, "Aug 2026–Apr 2027 (8 months)")

    def test_contract_period_label_january(self):
        label = contract_period_label(1, 3)
        self.assertEqual(label, "Jan 2027–Apr 2027 (3 months)")

    def test_contract_period_label_april(self):
        label = contract_period_label(4, 12)
        self.assertEqual(label, "Apr 2026–Apr 2027 (12 months)")

    def test_contract_period_label_march(self):
        label = contract_period_label(3, 1)
        self.assertEqual(label, "Mar 2027–Apr 2027 (1 month)")

    def test_pro_rate_days_zero_annual(self):
        self.assertEqual(pro_rate_days(0, 12), 0)
        self.assertEqual(pro_rate_days(0, 8), 0)

    def test_pro_rate_contract_full_year(self):
        months, days, label = pro_rate_contract(240, None)
        self.assertEqual(months, 12)
        self.assertEqual(days, 240)
        self.assertIsNone(label)

    def test_pro_rate_contract_august(self):
        months, days, label = pro_rate_contract(240, 8)
        self.assertEqual(months, 8)
        self.assertEqual(days, 160)
        self.assertEqual(label, "Aug 2026–Apr 2027 (8 months)")

    def test_pro_rate_contract_january(self):
        months, days, label = pro_rate_contract(240, 1)
        self.assertEqual(months, 3)
        self.assertEqual(days, 60)
        self.assertEqual(label, "Jan 2027–Apr 2027 (3 months)")


if __name__ == "__main__":
    unittest.main()
