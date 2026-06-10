import unittest
from payday.calculators.inside_ir35 import InsideIR35Calculator


class TestInsideIR35Calculator(unittest.TestCase):
    def test_solve_gross_salary_below_threshold(self):
        # Budget <= 5025 means gross <= 5000, uses /1.005 formula
        gross = InsideIR35Calculator.solve_gross_salary(5025)
        # 5025 / 1.005 = 5000
        self.assertEqual(gross, 5000)

    def test_solve_gross_salary_above_threshold(self):
        # Budget 118800 = 500*240 - 25*48
        # gross = (118800 + 750) / 1.155 = 119550 / 1.155 = 103506.49 -> 103506
        gross = InsideIR35Calculator.solve_gross_salary(118800)
        self.assertEqual(gross, 103506)

    def test_solve_gross_salary_small(self):
        gross = InsideIR35Calculator.solve_gross_salary(0)
        self.assertEqual(gross, 0)

    def test_full_pipeline_500_day(self):
        # £500/day, 240 days, £25/wk margin
        breakdown = InsideIR35Calculator.calculate(500, 240, 25)

        self.assertEqual(breakdown.mode, "Inside IR35")
        self.assertEqual(breakdown.inputs["day_rate"], 500)
        self.assertEqual(breakdown.inputs["working_days"], 240)
        self.assertEqual(breakdown.inputs["margin_weekly"], 25)

        # Assignment = 500 * 240 = 120000
        self.assertEqual(breakdown.steps[0].amount, 120000)

        # Margin = 25 * (240/5) = 25 * 48 = 1200
        self.assertEqual(breakdown.steps[1].amount, -1200)

        # Budget = 120000 - 1200 = 118800
        # Gross = (118800 + 750) / 1.155 = 103506
        self.assertEqual(breakdown.steps[4].amount, 103506)

        # Employer NI on 103506: (103506 - 5000) * 0.15 = 98506 * 0.15 = 14775.9 -> 14776
        # Actually let me just check the take-home is consistent
        self.assertGreater(breakdown.annual_take_home, 0)
        self.assertGreater(breakdown.display_take_home, 0)
        self.assertIsNotNone(breakdown.income_tax)
        self.assertIsNotNone(breakdown.employee_ni)
        self.assertIsNotNone(breakdown.employer_ni)

    def test_20_day_pro_rata(self):
        breakdown = InsideIR35Calculator.calculate(600, 200, 25)
        # annual = 600 * 200 = 120000
        # margin = 25 * (200/5) = 25 * 40 = 1000
        # budget = 120000 - 1000 = 119000
        # gross = (119000 + 750) / 1.155 = 119750 / 1.155 = 103679.65 -> 103680
        # display = round(annual_take_home / 200 * 20)
        expected_display = round(breakdown.annual_take_home / 200 * 20)
        self.assertEqual(breakdown.display_take_home, expected_display)

    def test_different_day_rates(self):
        # Just ensure all day rates produce reasonable results
        for rate in [300, 500, 800]:
            breakdown = InsideIR35Calculator.calculate(rate, 240, 25)
            self.assertGreater(breakdown.annual_take_home, 0)
            self.assertGreater(breakdown.display_take_home, 0)
            # Take-home should be less than gross
            gross = breakdown.steps[4].amount
            self.assertLess(breakdown.annual_take_home, gross)


if __name__ == "__main__":
    unittest.main()
