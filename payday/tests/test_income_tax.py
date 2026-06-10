import unittest
from payday.income_tax import calc_personal_allowance, calc_income_tax


class TestIncomeTax(unittest.TestCase):
    def test_personal_allowance_standard(self):
        pa, tapered = calc_personal_allowance(50000)
        self.assertEqual(pa, 12570)
        self.assertFalse(tapered)

    def test_personal_allowance_taper_start(self):
        pa, tapered = calc_personal_allowance(100000)
        self.assertEqual(pa, 12570)
        self.assertFalse(tapered)

    def test_personal_allowance_tapered(self):
        pa, tapered = calc_personal_allowance(110000)
        self.assertEqual(pa, 7570)
        self.assertTrue(tapered)

    def test_personal_allowance_zeroed(self):
        pa, tapered = calc_personal_allowance(125140)
        self.assertEqual(pa, 0)
        self.assertTrue(tapered)

    def test_personal_allowance_highly_tapered(self):
        pa, tapered = calc_personal_allowance(200000)
        self.assertEqual(pa, 0)
        self.assertTrue(tapered)

    def test_income_tax_basic_rate(self):
        # Salary 50k, PA 12570 -> Taxable 37430
        # 37430 * 0.20 = 7486
        res = calc_income_tax(50000, 12570)
        self.assertEqual(res.total_tax, 7486)
        self.assertEqual(res.basic_tax, 7486)
        self.assertEqual(res.higher_tax, 0)

    def test_income_tax_higher_rate(self):
        # Salary 80k, PA 12570 -> Taxable 67430
        # Basic: 37700 * 0.20 = 7540
        # Higher: (67430 - 37700) * 0.40 = 29730 * 0.40 = 11892
        # Total: 7540 + 11892 = 19432
        res = calc_income_tax(80000, 12570)
        self.assertEqual(res.total_tax, 19432)

    def test_income_tax_additional_rate(self):
        # Salary 150k, PA 0 -> Taxable 150000
        # Basic (20%):  37700 * 0.20 =  7540
        # Higher (40%): (125140 - 37700) * 0.40 = 87440 * 0.40 = 34976
        # Additional (45%): (150000 - 125140) * 0.45 = 24860 * 0.45 = 11187
        # Total: 7540 + 34976 + 11187 = 53703
        res = calc_income_tax(150000, 0)
        self.assertEqual(res.total_tax, 53703)


if __name__ == "__main__":
    unittest.main()
