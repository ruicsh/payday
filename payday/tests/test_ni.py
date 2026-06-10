import unittest
from payday.national_insurance import calc_employee_ni, calc_employer_ni


class TestNationalInsurance(unittest.TestCase):
    def test_ee_ni_zero(self):
        res = calc_employee_ni(0)
        self.assertEqual(res.total_ni, 0)
        self.assertEqual(res.below_pt, 0)

    def test_ee_ni_below_threshold(self):
        res = calc_employee_ni(12570)
        self.assertEqual(res.total_ni, 0)
        self.assertEqual(res.below_pt, 12570)

    def test_ee_ni_main_rate_only(self):
        # Salary 50k: (50000 - 12570) * 0.08 = 37430 * 0.08 = 2994.4 -> 2994
        res = calc_employee_ni(50000)
        self.assertEqual(res.total_ni, 2994)
        self.assertEqual(res.main_band, 37430)

    def test_ee_ni_upper_rate(self):
        # Salary 100k: main: 37700 * 0.08 = 3016, upper: (100k-50270) * 0.02 = 49730 * 0.02 = 994.6 -> 995
        # Total: 3016 + 995 = 4011
        res = calc_employee_ni(100000)
        self.assertEqual(res.total_ni, 4011)

    def test_ee_ni_exact_upper_limit(self):
        res = calc_employee_ni(50270)
        self.assertEqual(res.upper_band, 0)
        # (50270 - 12570) * 0.08 = 37700 * 0.08 = 3016
        self.assertEqual(res.total_ni, 3016)

    def test_er_ni_zero(self):
        res = calc_employer_ni(0)
        self.assertEqual(res.total_er_ni, 0)

    def test_er_ni_below_secondary(self):
        res = calc_employer_ni(5000)
        self.assertEqual(res.total_er_ni, 0)
        self.assertEqual(res.below_st, 5000)

    def test_er_ni_above_secondary(self):
        # (50000 - 5000) * 0.15 = 45000 * 0.15 = 6750
        res = calc_employer_ni(50000)
        self.assertEqual(res.total_er_ni, 6750)
        self.assertEqual(res.above_st, 45000)

    def test_er_ni_high(self):
        # (100000 - 5000) * 0.15 = 95000 * 0.15 = 14250
        res = calc_employer_ni(100000)
        self.assertEqual(res.total_er_ni, 14250)


if __name__ == "__main__":
    unittest.main()
