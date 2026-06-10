import unittest
from payday.pension import calc_pension


class TestPension(unittest.TestCase):
    def test_below_trigger(self):
        # Salary <= 10,000 should not be auto-enrolled
        result = calc_pension(10_000)
        self.assertFalse(result.eligible)
        self.assertEqual(result.employee_contribution, 0)
        self.assertEqual(result.employer_contribution, 0)

    def test_above_trigger_below_uel(self):
        # Salary = 30,000
        # Qualifying earnings = 30,000 - 6,240 = 23,760
        # Employee (5%) = 23,760 * 0.05 = 1,188 -> 1,188
        # Employer (3%) = 23,760 * 0.03 = 712.8 -> 713
        result = calc_pension(30_000)
        self.assertTrue(result.eligible)
        self.assertEqual(result.qualifying_earnings, 30_000 - 6_240)
        self.assertEqual(result.employee_contribution, 1_188)
        self.assertEqual(result.employer_contribution, 713)

    def test_above_uel(self):
        # Salary = 60,000 (Above UEL 50,270)
        # Qualifying earnings = 50,270 - 6,240 = 44,030
        # Employee (5%) = 44,030 * 0.05 = 2,201.5 -> 2,202
        # Employer (3%) = 44,030 * 0.03 = 1,320.9 -> 1,321
        result = calc_pension(60_000)
        self.assertTrue(result.eligible)
        self.assertEqual(result.qualifying_earnings, 50_270 - 6_240)
        self.assertEqual(result.employee_contribution, 2_202)
        self.assertEqual(result.employer_contribution, 1_321)

    def test_exact_trigger(self):
        # 10,001 should be enrolled
        result = calc_pension(10_001)
        self.assertTrue(result.eligible)
        # Qualifying = 10,001 - 6,240 = 3,761
        # Employee = 3,761 * 0.05 = 188.05 -> 188
        self.assertEqual(result.employee_contribution, 188)


if __name__ == "__main__":
    unittest.main()
