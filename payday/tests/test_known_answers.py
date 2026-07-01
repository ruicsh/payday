import unittest
from payday.income_tax import calc_adjusted_net_income, calc_income_tax, calc_personal_allowance
from payday.national_insurance import calc_employee_ni
from payday.corporation_tax import calc_corporation_tax


class TestKnownAnswers(unittest.TestCase):
    """Integration tests using known answers from GOV.UK examples."""

    def test_income_tax_50k(self):
        # GOV.UK Example: £50,000 salary
        # PA: £12,570
        # Taxable: £37,430
        # 20% Tax: £7,486
        ani = calc_adjusted_net_income(employment_income=50000)
        pa, tapered = calc_personal_allowance(ani)
        res = calc_income_tax(50000, pa)
        self.assertEqual(res.total_tax, 7486)
        self.assertFalse(tapered)

    def test_ni_employee_50k(self):
        # NI Category A: £50,000 salary
        # (£50,000 - £12,570) * 8% = £2,994.40 -> £2,994
        res = calc_employee_ni(50000)
        self.assertEqual(res.total_ni, 2994)

    def test_corporation_tax_100k(self):
        # Profit £100,000
        # Tax: (£100,000 * 25%) - (250,000 - 100,000) * 3/200
        # = 25,000 - 2,250 = 22,750
        res = calc_corporation_tax(100000)
        self.assertEqual(res.total_ct, 22750)

    def test_income_tax_150k(self):
        # Salary £150,000
        # PA: 0
        # Taxable: £150,000
        # Basic: 37,700 * 0.20 = 7,540
        # Higher: (125,140 - 37,700) * 0.40 = 34,976
        # Additional: (150,000 - 125,140) * 0.45 = 11,187
        # Total: 53,703
        ani = calc_adjusted_net_income(employment_income=150000)
        pa, tapered = calc_personal_allowance(ani)
        res = calc_income_tax(150000, pa)
        self.assertEqual(res.total_tax, 53703)
        self.assertTrue(tapered)


if __name__ == "__main__":
    unittest.main()
