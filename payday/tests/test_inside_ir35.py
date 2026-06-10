import unittest
from payday.calculators.inside_ir35 import InsideIR35Calculator


class TestInsideIR35Calculator(unittest.TestCase):
    def _find_step(self, breakdown, label):
        """Helper to find a step by its label."""
        for step in breakdown.steps:
            if step.label == label:
                return step
        self.fail(f"Step with label '{label}' not found in breakdown")

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
        self.assertEqual(self._find_step(breakdown, "Assignment Rate").amount, 120000)

        # Margin = 25 * (240/5) = 25 * 48 = 1200
        self.assertEqual(self._find_step(breakdown, "Umbrella Margin").amount, -1200)

        # Budget = 120000 - 1200 = 118800
        # Gross = (118800 + 750) / 1.155 = 103506
        self.assertEqual(self._find_step(breakdown, "Gross Salary").amount, 103506)

        # New steps: PA and Taxable Income
        # PA for 103506: 12570 - (103506-100000)/2 = 12570 - 1753 = 10817
        self.assertEqual(self._find_step(breakdown, "Personal Allowance (tapered)").amount, -10817)
        self.assertEqual(self._find_step(breakdown, "Taxable Income").amount, 103506 - 10817)

        # Verify take-home and sub-results are present
        self.assertGreater(breakdown.annual_take_home, 0)
        self.assertGreater(breakdown.display_take_home, 0)
        self.assertIsNotNone(breakdown.income_tax)
        self.assertIsNotNone(breakdown.employee_ni)
        self.assertIsNotNone(breakdown.employer_ni)

    def test_tapered_personal_allowance_high_rate(self):
        # £1000/day, 240 days = 240,000 assignment
        # margin = 1200
        # budget = 238800
        # gross = (238800 + 750) / 1.155 = 207403
        # PA should be 0 (tapered)
        breakdown = InsideIR35Calculator.calculate(1000, 240, 25)
        
        self.assertEqual(self._find_step(breakdown, "Personal Allowance (tapered)").amount, 0)
        self.assertEqual(self._find_step(breakdown, "Taxable Income").amount, 207403)

    def test_non_tapered_personal_allowance_low_rate(self):
        # £300/day, 240 days = 72,000 assignment
        # margin = 1200
        # budget = 70800
        # gross = (70800 + 750) / 1.155 = 61948
        # PA should be 12570 (not tapered)
        breakdown = InsideIR35Calculator.calculate(300, 240, 25)
        
        self.assertEqual(self._find_step(breakdown, "Personal Allowance").amount, -12570)
        self.assertEqual(self._find_step(breakdown, "Taxable Income").amount, 61948 - 12570)

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
