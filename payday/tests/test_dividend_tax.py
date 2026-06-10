import unittest
from payday.dividend_tax import calc_dividend_tax


class TestDividendTax(unittest.TestCase):
    def test_no_dividends(self):
        res = calc_dividend_tax(0, 50000)
        self.assertEqual(res.total_tax, 0)
        self.assertEqual(res.dividend_allowance, 0)

    def test_dividends_within_allowance(self):
        res = calc_dividend_tax(500, 12570)
        self.assertEqual(res.total_tax, 0)
        self.assertEqual(res.dividend_allowance, 500)
        self.assertEqual(res.taxable_dividends, 0)

    def test_dividends_basic_rate_only(self):
        # Salary 12570 (PA fully consumed), dividends 40000
        # Allowance: 500 at 0%
        # Remaining: 39500
        # Basic band: 37700 total, 500 consumed by allowance, 37200 at 10.75%
        # Higher band: 39500 - 37200 = 2300 at 35.75%
        # Total: 37200*0.1075 + 2300*0.3575 = 3999.0 + 822.25 = 4821.25 -> 4821
        res = calc_dividend_tax(40000, 12570)
        self.assertEqual(res.total_tax, 4821)
        self.assertEqual(res.basic_band, 37200)
        self.assertEqual(res.higher_band, 2300)

    def test_salary_uses_some_basic_band(self):
        # Salary 30000, PA 12570 -> taxable_salary = 17430
        # Dividends 30000, allowance 500, remaining 29500
        # Basic band: 37700 - 17430 = 20270 remaining
        # Allowance consumes 500, so 19770 at 10.75%
        # Higher: 29500 - 19770 = 9730 at 35.75%
        # Total: 19770*0.1075 + 9730*0.3575 = 2125.275 + 3478.475 = 5603.75 -> 5604?
        # round(2125.275)=2125, round(3478.475)=3478, total=5603
        res = calc_dividend_tax(30000, 30000)
        self.assertEqual(res.total_tax, 5603)
        self.assertEqual(res.basic_band, 19770)
        self.assertEqual(res.higher_band, 9730)

    def test_high_dividends_cross_into_additional(self):
        # Salary 12570, PA=12570 (total income 212570, fully tapered to 0)
        # taxable_salary = 12570 (since PA=0)
        # Taxable dividends = 200000, allowance = 500, remaining = 199500
        # Basic band: 37700 total, 12570 consumed by salary, 25130 remaining
        #   allowance uses 500, so 24630 at 10.75% -> 2648
        # Higher band: 74870 total, 0 consumed by salary, 74870 remaining
        #   min(199500-24630, 74870) = 74870 at 35.75% -> 26766
        # Additional: 199500-24630-74870 = 100000 at 39.35% -> 39350
        # Total: 2648 + 26766 + 39350 = 68764
        res = calc_dividend_tax(200000, 12570)
        self.assertEqual(res.total_tax, 68764)
        self.assertEqual(res.additional_band, 100000)

    def test_dividends_within_allowance_no_salary(self):
        # Salary 0, dividends 500
        # PA = 12570 (total_income = 500, no taper)
        # taxable_salary = 0
        # allowance = 500, remaining = 0
        # No tax
        res = calc_dividend_tax(500, 0)
        self.assertEqual(res.total_tax, 0)

    def test_dividends_fully_in_basic_no_salary(self):
        # Salary 0, dividends 38000
        # PA = 12570 (total_income = 38000, no taper)
        # taxable_salary = 0
        # allowance = 500
        # Basic band = 37700 - 0 = 37700 total, 500 allowance, 37200 taxable
        # remaining = 38000 - 500 = 37500
        # div_basic = min(37500, 37200) = 37200 at 10.75%
        # remaining = 37500 - 37200 = 300
        # higher = 300 at 35.75%
        # total = 37200*0.1075 + 300*0.3575 = 3999 + 107.25 = 4106.25 -> 4106
        # round(3999.0)=3999, round(107.25)=107, total=4106
        res = calc_dividend_tax(38000, 0)
        self.assertEqual(res.total_tax, 4106)


if __name__ == "__main__":
    unittest.main()
