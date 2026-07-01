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
        # Budget > 58633 (Case C→D boundary), so Case D applies:
        # gross = (118800 - 570.90) / 1.155 = 102362.8 -> 102363
        gross = InsideIR35Calculator.solve_gross_salary(118800)
        self.assertEqual(gross, 102363)

    def test_solve_gross_salary_pension_band(self):
        # Budget 30000 (Case C: 10800 < B <= 58633)
        # gross = (30000 + 937.20) / 1.185 = 30937.20 / 1.185 = 26107.34 -> 26107
        gross = InsideIR35Calculator.solve_gross_salary(30000)
        self.assertEqual(gross, 26107)

    def test_solve_gross_salary_no_pension_band(self):
        # Budget 8000 (Case B: 5025 < B <= 10800)
        # gross = (8000 + 750) / 1.155 = 8750 / 1.155 = 7575.75 -> 7576
        gross = InsideIR35Calculator.solve_gross_salary(8000)
        self.assertEqual(gross, 7576)

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
        # Gross = (118800 - 570.90) / 1.155 = 102363
        self.assertEqual(self._find_step(breakdown, "Gross Salary").amount, 102363)

        # New steps: PA and Taxable Income
        # PA for 102363: 12570 - int((102363-100000)/2) = 12570 - 1181 = 11389
        self.assertEqual(
            self._find_step(breakdown, "Personal Allowance (tapered)").amount, -11389
        )
        self.assertEqual(
            self._find_step(breakdown, "Taxable Income").amount, 102363 - 11389
        )

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
        # gross = (238800 - 570.90) / 1.155 = 206259
        # PA should be 0 (tapered)
        breakdown = InsideIR35Calculator.calculate(1000, 240, 25)

        self.assertEqual(
            self._find_step(breakdown, "Personal Allowance (tapered)").amount, 0
        )
        self.assertEqual(self._find_step(breakdown, "Taxable Income").amount, 206259)

    def test_non_tapered_personal_allowance_low_rate(self):
        # £300/day, 240 days = 72,000 assignment
        # margin = 1200
        # budget = 70800
        # gross = (70800 - 570.90) / 1.155 = 60804
        # PA should be 12570 (not tapered)
        breakdown = InsideIR35Calculator.calculate(300, 240, 25)

        self.assertEqual(
            self._find_step(breakdown, "Personal Allowance").amount, -12570
        )
        self.assertEqual(
            self._find_step(breakdown, "Taxable Income").amount, 60804 - 12570
        )

    def test_20_day_pro_rata(self):
        breakdown = InsideIR35Calculator.calculate(600, 200, 25)
        # annual = 600 * 200 = 120000
        # margin = 25 * (200/5) = 25 * 40 = 1000
        # budget = 120000 - 1000 = 119000
        # Case D applies: gross = (119000 - 570.90) / 1.155
        # display = round(annual_take_home / 200 * 20)
        expected_display = round(breakdown.annual_take_home / 200 * 20)
        self.assertEqual(breakdown.display_take_home, expected_display)

    def test_partial_year_august_start(self):
        # £500/day, 240 days/yr, £25/wk, start Aug → 8 months → 160 days
        breakdown = InsideIR35Calculator.calculate(500, 240, 25, start_month=8)

        self.assertEqual(breakdown.inputs["start_month"], 8)
        self.assertEqual(breakdown.inputs["contract_months"], 8)
        self.assertEqual(breakdown.inputs["effective_working_days"], 160)
        self.assertEqual(
            breakdown.inputs["contract_period"], "Aug 2026–Apr 2027 (8 months)"
        )

        # Assignment = 500 * 160 = 80000 (vs 120000 full year)
        self.assertEqual(self._find_step(breakdown, "Assignment Rate").amount, 80000)

        # 20-day pay = annual_take_home / 160 * 20
        expected_display = round(breakdown.annual_take_home / 160 * 20)
        self.assertEqual(breakdown.display_take_home, expected_display)

    def test_partial_year_january_start(self):
        # £500/day, 240 days/yr, £25/wk, start Jan → 3 months → 60 days
        breakdown = InsideIR35Calculator.calculate(500, 240, 25, start_month=1)

        self.assertEqual(breakdown.inputs["contract_months"], 3)
        self.assertEqual(breakdown.inputs["effective_working_days"], 60)

        # Assignment = 500 * 60 = 30000
        self.assertEqual(self._find_step(breakdown, "Assignment Rate").amount, 30000)

        expected_display = round(breakdown.annual_take_home / 60 * 20)
        self.assertEqual(breakdown.display_take_home, expected_display)

    def test_partial_year_no_start_month_identical_to_full_year(self):
        # Calling with start_month=None should produce same result as not passing it
        with_start = InsideIR35Calculator.calculate(500, 240, 25, start_month=None)
        without = InsideIR35Calculator.calculate(500, 240, 25)
        self.assertEqual(with_start.annual_take_home, without.annual_take_home)
        self.assertEqual(with_start.display_take_home, without.display_take_home)
        self.assertNotIn("contract_period", with_start.inputs)

    def test_zero_working_days_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "working_days must be > 0"):
            InsideIR35Calculator.calculate(500, 0, 25)

    def test_different_day_rates(self):
        # Just ensure all day rates produce reasonable results
        for rate in [300, 500, 800]:
            breakdown = InsideIR35Calculator.calculate(rate, 240, 25)
            self.assertGreater(breakdown.annual_take_home, 0)
            self.assertGreater(breakdown.display_take_home, 0)
            # Take-home should be less than gross
            gross = self._find_step(breakdown, "Gross Salary").amount
            self.assertLess(breakdown.annual_take_home, gross)


if __name__ == "__main__":
    unittest.main()
