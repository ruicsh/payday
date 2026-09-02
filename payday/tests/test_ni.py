import unittest
from payday.national_insurance import calc_employee_ni, calc_employer_ni


class TestNationalInsurance(unittest.TestCase):
    def test_ee_ni_zero(self):
        res = calc_employee_ni(0)
        self.assertEqual(res.total_ni, 0)
        self.assertEqual(res.below_pt, 0)

    def test_ee_ni_at_primary_threshold(self):
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


class TestNationalInsuranceCategoryB(unittest.TestCase):
    """Married women / widows reduced-rate election (1.85% main rate)."""

    def test_ee_ni_reduced_rate(self):
        # (50000 - 12570) * 0.0185 = 37430 * 0.0185 = 692.455 -> 692
        res = calc_employee_ni(50000, "B")
        self.assertEqual(res.total_ni, 692)
        self.assertEqual(res.main_band, 37430)

    def test_ee_ni_reduced_rate_upper(self):
        # main: 37700 * 0.0185 = 697.45 -> 697; upper: 49730 * 0.02 = 994.6 -> 995
        res = calc_employee_ni(100000, "B")
        self.assertEqual(res.total_ni, 697 + 995)


class TestNationalInsuranceCategoryC(unittest.TestCase):
    """Over State Pension age — no employee NI."""

    def test_ee_ni_zero_all_bands(self):
        for salary in (0, 12570, 50000, 100000):
            res = calc_employee_ni(salary, "C")
            self.assertEqual(res.total_ni, 0)
            self.assertEqual(res.main_ni, 0)
            self.assertEqual(res.upper_ni, 0)
            self.assertEqual(res.main_band, 0)
            self.assertEqual(res.upper_band, 0)
            self.assertEqual(res.below_pt, salary)


class TestNationalInsuranceCategoryZ(unittest.TestCase):
    """Under-21 deferment — 2% flat above the primary threshold."""

    def test_ee_ni_deferred_flat_rate(self):
        # 2% on everything above the primary threshold
        # 50k: (50000 - 12570) * 0.02 = 748.6 -> 749
        res = calc_employee_ni(50000, "Z")
        self.assertEqual(res.total_ni, 749)
        # 100k: (100000 - 12570) * 0.02 = 1748.6 -> 1749
        self.assertEqual(calc_employee_ni(100000, "Z").total_ni, 1749)


class TestNationalInsuranceCategoryValidation(unittest.TestCase):
    def test_case_insensitive(self):
        self.assertEqual(calc_employee_ni(50000, "b").total_ni, 692)
        self.assertEqual(calc_employee_ni(50000, "z").total_ni, 749)

    def test_unknown_category_raises(self):
        for bad in ("X", "H", "M", "V"):
            with self.assertRaises(ValueError):
                calc_employee_ni(50000, bad)


if __name__ == "__main__":
    unittest.main()
