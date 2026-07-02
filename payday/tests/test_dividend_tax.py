import unittest
from payday.dividend_tax import calc_dividend_tax
from payday.models import DividendTaxResult


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

    # ── existing_income tests ──────────────────────────────────────────

    def test_dividend_tax_with_existing_income(self):
        # Existing £30k, director salary £12,570, dividends £50k.
        # Total employment: £42,570 consumes £30k of basic band.
        # Remaining basic band: £7,700, minus £500 allowance = £7,200.
        # Higher band consumes rest.
        res = calc_dividend_tax(50000, 12570, existing_income=30000)
        self.assertEqual(res.total_tax, 15896)
        self.assertEqual(res.basic_band, 7200)
        self.assertEqual(res.higher_band, 42300)

    def test_dividend_tax_existing_backward_compatible(self):
        res_default = calc_dividend_tax(40000, 12570)
        res_explicit = calc_dividend_tax(40000, 12570, existing_income=0)
        self.assertEqual(res_default.total_tax, res_explicit.total_tax)

    def test_dividend_tax_existing_fully_consumes_basic(self):
        # Existing £50k + salary £12,570 = £62,570, PA £12,570.
        # taxable_employment = £50k. All £37,700 basic band consumed.
        # Dividends: £500 allowance, rest all at higher rate.
        res = calc_dividend_tax(20000, 12570, existing_income=50000)
        # remaining_dividends = 19,500
        # basic_for_taxable_dividends = 37,700 - 37,700 = 0 (all consumed)
        # div_basic_band = 0
        # div_higher_band = min(19,500, 74,870) = 19,500
        # tax = 19,500 * 0.3575 = 6,971 -> round = 6971
        self.assertEqual(res.total_tax, 6971)
        self.assertEqual(res.basic_band, 0)
        self.assertEqual(res.higher_band, 19500)

    def test_dividend_tax_existing_income_float(self):
        """Float existing_income should be accepted in dividend tax calc."""
        res = calc_dividend_tax(50000, 12570, existing_income=30000.50)
        self.assertIsInstance(res, DividendTaxResult)
        # Result should be within £1 of the int case (£15,896)
        self.assertEqual(res.total_tax, 15896)
        # Bands should be valid (non-negative, reasonable)
        self.assertGreaterEqual(res.basic_band, 7199)
        self.assertLessEqual(res.basic_band, 7200)
        self.assertGreaterEqual(res.higher_band, 42300)
        self.assertLessEqual(res.higher_band, 42301)

    # ── existing_dividends tests ─────────────────────────────────────

    def test_dividend_tax_existing_dividends_consumes_allowance(self):
        # Existing £400 dividends consume most of the £500 allowance.
        # New £40,000 dividends: only £100 allowance left, pushing more into higher rate.
        # Without existing: £48,221. With existing £400: marginal tax £4,964.
        res = calc_dividend_tax(40000, 12570, existing_dividends=400)
        self.assertEqual(res.total_tax, 4964)
        self.assertEqual(res.dividend_allowance, 100)
        self.assertEqual(res.taxable_dividends, 39900)
        self.assertEqual(res.basic_band, 37200)
        self.assertEqual(res.higher_band, 2700)

    def test_dividend_tax_existing_dividends_fully_consumes_allowance(self):
        # Existing £500 dividends consume all of the £500 allowance.
        res = calc_dividend_tax(40000, 12570, existing_dividends=500)
        self.assertEqual(res.total_tax, 5000)
        self.assertEqual(res.dividend_allowance, 0)
        self.assertEqual(res.taxable_dividends, 40000)

    def test_dividend_tax_existing_dividends_push_into_higher(self):
        # Existing £37,500 dividends fill almost all basic band.
        # New £5,000 dividends: taxed in higher rate band (no basic band left).
        res = calc_dividend_tax(5000, 12570, existing_dividends=37500)
        self.assertEqual(res.total_tax, 1737)
        self.assertEqual(res.dividend_allowance, 0)
        self.assertEqual(res.taxable_dividends, 5000)

    def test_dividend_tax_existing_dividends_backward_compatible(self):
        res_default = calc_dividend_tax(40000, 12570)
        res_explicit = calc_dividend_tax(40000, 12570, existing_dividends=0)
        self.assertEqual(res_default.total_tax, res_explicit.total_tax)

    def test_dividend_tax_existing_dividends_no_new_dividends(self):
        # Only existing dividends, no new dividends being taken.
        res = calc_dividend_tax(0, 12570, existing_dividends=400)
        self.assertEqual(res.total_tax, 0)
        self.assertEqual(res.dividend_allowance, 0)
        self.assertEqual(res.taxable_dividends, 0)

    def test_dividend_tax_existing_dividends_float(self):
        res = calc_dividend_tax(40000, 12570, existing_dividends=400.50)
        self.assertIsInstance(res, DividendTaxResult)
        self.assertEqual(res.total_tax, 4964)
        self.assertEqual(res.dividend_allowance, 100)
        self.assertEqual(res.taxable_dividends, 39900)


if __name__ == "__main__":
    unittest.main()
