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

    def test_solve_gross_salary_without_er_pension_low(self):
        """Budget <= 5025: same formula with or without ER pension."""
        gross = InsideIR35Calculator.solve_gross_salary(5025, include_er_pension=False)
        self.assertEqual(gross, round(5025 / 1.005))

    def test_solve_gross_salary_without_er_pension_mid(self):
        """Mid budget: uses case B formula (ER NI + Levy, no ER pension)."""
        gross = InsideIR35Calculator.solve_gross_salary(30000, include_er_pension=False)
        self.assertEqual(gross, round((30000 + 750) / 1.155))

    def test_solve_gross_salary_without_er_pension_high(self):
        """High budget: same case B formula (ER pension cap doesn't apply)."""
        gross = InsideIR35Calculator.solve_gross_salary(118800, include_er_pension=False)
        self.assertEqual(gross, round((118800 + 750) / 1.155))

    def test_solve_gross_salary_backward_compatible_default(self):
        """Default (include_er_pension=True) preserves existing behavior."""
        with_default = InsideIR35Calculator.solve_gross_salary(30000)
        with_explicit = InsideIR35Calculator.solve_gross_salary(30000, include_er_pension=True)
        self.assertEqual(with_default, with_explicit)

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

    # ── salary_sacrifice tests ─────────────────────────────────────────

    def test_salary_sacrifice_backward_compatible_default(self):
        """Calling with salary_sacrifice=0 should match default."""
        default = InsideIR35Calculator.calculate(500, 240, 25)
        explicit = InsideIR35Calculator.calculate(500, 240, 25, salary_sacrifice=0)
        self.assertEqual(default.annual_take_home, explicit.annual_take_home)
        self.assertEqual(default.steps, explicit.steps)

    def test_salary_sacrifice_adds_waterfall_steps(self):
        """With a sacrifice, the waterfall shows Salary Sacrifice and ER NI Saved to SIPP."""
        breakdown = InsideIR35Calculator.calculate(500, 240, 25, salary_sacrifice=5000)
        self._find_step(breakdown, "Salary Sacrifice")
        self._find_step(breakdown, "ER NI Saved to SIPP")
        self.assertIn("salary_sacrifice", breakdown.inputs)
        self.assertEqual(breakdown.inputs["salary_sacrifice"], 5000)

    def test_salary_sacrifice_reduces_tax_and_ni(self):
        """A sacrifice of £15k on £300/day reduces IT and NI; pension is skipped."""
        no_sac = InsideIR35Calculator.calculate(300, 240, 25)
        with_sac = InsideIR35Calculator.calculate(300, 240, 25, salary_sacrifice=15000)

        self.assertLess(with_sac.income_tax.total_tax, no_sac.income_tax.total_tax)
        self.assertLess(with_sac.employee_ni.total_ni, no_sac.employee_ni.total_ni)
        self.assertEqual(with_sac.pension.employee_contribution, 0)
        self.assertEqual(with_sac.pension.employer_contribution, 0)

    def test_salary_sacrifice_take_home_savings(self):
        """£15k sacrifice should reduce take-home by less than £15k due to savings."""
        no_sac = InsideIR35Calculator.calculate(500, 240, 25)
        with_sac = InsideIR35Calculator.calculate(500, 240, 25, salary_sacrifice=15000)

        reduction = no_sac.annual_take_home - with_sac.annual_take_home
        self.assertGreater(reduction, 0)
        self.assertLess(reduction, 15000)

    def test_salary_sacrifice_combined_with_existing_income(self):
        """Salary sacrifice works alongside existing income and partial year."""
        breakdown = InsideIR35Calculator.calculate(
            500, 240, 25, start_month=8, existing_income=30000, salary_sacrifice=5000
        )

        self.assertIn("salary_sacrifice", breakdown.inputs)
        self._find_step(breakdown, "Salary Sacrifice")
        self.assertGreater(breakdown.annual_take_home, 0)
        self.assertGreater(breakdown.display_take_home, 0)

    def test_salary_sacrifice_skips_auto_enrolment(self):
        """With sacrifice, auto-enrolment pension is skipped entirely."""
        breakdown = InsideIR35Calculator.calculate(200, 240, 25, salary_sacrifice=5000)
        self.assertEqual(breakdown.pension.employee_contribution, 0)
        self.assertEqual(breakdown.pension.employer_contribution, 0)
        self.assertFalse(breakdown.pension.eligible)
        labels = {step.label for step in breakdown.steps}
        self.assertNotIn("Employer Pension (3%)", labels)
        self.assertNotIn("Pension Contribution", labels)

    def test_salary_sacrifice_er_ni_saving_computed(self):
        """With sacrifice, ER NI saving is positive and present in waterfall."""
        breakdown = InsideIR35Calculator.calculate(500, 240, 25, salary_sacrifice=5000)
        saving_step = self._find_step(breakdown, "ER NI Saved to SIPP")
        self.assertGreater(saving_step.amount, 0)
        self.assertIn("er_ni_saving", breakdown.inputs)
        self.assertGreater(breakdown.inputs["er_ni_saving"], 0)

    def test_different_day_rates(self):
        # Just ensure all day rates produce reasonable results
        for rate in [300, 500, 800]:
            breakdown = InsideIR35Calculator.calculate(rate, 240, 25)
            self.assertGreater(breakdown.annual_take_home, 0)
            self.assertGreater(breakdown.display_take_home, 0)
            # Take-home should be less than gross
            gross = self._find_step(breakdown, "Gross Salary").amount
            self.assertLess(breakdown.annual_take_home, gross)

    # ── existing_income tests ──────────────────────────────────────────

    def test_partial_year_existing_backward_compatible(self):
        no_existing = InsideIR35Calculator.calculate(500, 240, 25, start_month=8)
        explicit_zero = InsideIR35Calculator.calculate(
            500, 240, 25, start_month=8, existing_income=0
        )
        self.assertEqual(no_existing.annual_take_home, explicit_zero.annual_take_home)
        self.assertEqual(no_existing.display_take_home, explicit_zero.display_take_home)

    def test_partial_year_with_existing_income(self):
        # £500/day, 240 days/yr, £25/wk, Aug start (8mo), existing £30k
        breakdown = InsideIR35Calculator.calculate(
            500, 240, 25, start_month=8, existing_income=30000
        )

        self.assertIn("existing_income", breakdown.inputs)
        self.assertEqual(breakdown.inputs["existing_income"], 30000)

        # existing £30k fully consumes PA, so Personal Allowance line shows £0
        pa_step = self._find_step(breakdown, "Personal Allowance")
        self.assertEqual(pa_step.amount, 0)

        # Taxable income should be full gross (no remaining PA)
        gross = self._find_step(breakdown, "Gross Salary").amount
        taxable = self._find_step(breakdown, "Taxable Income").amount
        self.assertEqual(taxable, gross)

        # Income tax should be higher than without existing income
        without = InsideIR35Calculator.calculate(500, 240, 25, start_month=8)
        self.assertGreater(breakdown.income_tax.total_tax, without.income_tax.total_tax)

        # Take-home should be lower (more tax)
        self.assertLess(breakdown.annual_take_home, without.annual_take_home)

    def test_existing_income_triggers_pa_taper(self):
        # £600/day, Aug start (8mo/160d), existing £60k
        # Without existing: ANI ≈ 82k < 100k → no taper
        # With existing:    ANI ≈ 142k > 100k → taper
        breakdown = InsideIR35Calculator.calculate(
            600, 240, 25, start_month=8, existing_income=60000
        )

        self.assertLess(breakdown.income_tax.personal_allowance, 12570)
        self.assertTrue(breakdown.income_tax.tapered)

        without = InsideIR35Calculator.calculate(600, 240, 25, start_month=8)
        self.assertFalse(without.income_tax.tapered)


if __name__ == "__main__":
    unittest.main()
