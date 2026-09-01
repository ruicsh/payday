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
        gross = InsideIR35Calculator.solve_gross_salary(
            118800, include_er_pension=False
        )
        self.assertEqual(gross, round((118800 + 750) / 1.155))

    def test_solve_gross_salary_backward_compatible_default(self):
        """Default (include_er_pension=True) preserves existing behavior."""
        with_default = InsideIR35Calculator.solve_gross_salary(30000)
        with_explicit = InsideIR35Calculator.solve_gross_salary(
            30000, include_er_pension=True
        )
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

    def test_salary_sacrifice_exceeds_budget_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "exceeds available budget"):
            InsideIR35Calculator.calculate(500, 240, 25, salary_sacrifice=120000)

    # ── salary_sacrifice tests ─────────────────────────────────────────

    def test_salary_sacrifice_backward_compatible_default(self):
        """Calling with salary_sacrifice=0 should match default."""
        default = InsideIR35Calculator.calculate(500, 240, 25)
        explicit = InsideIR35Calculator.calculate(500, 240, 25, salary_sacrifice=0)
        self.assertEqual(default.annual_take_home, explicit.annual_take_home)
        self.assertEqual(default.steps, explicit.steps)

    def test_salary_sacrifice_adds_waterfall_steps(self):
        """With a sacrifice, the waterfall shows Salary Sacrifice and no auto-enrolment."""
        breakdown = InsideIR35Calculator.calculate(500, 240, 25, salary_sacrifice=5000)
        self._find_step(breakdown, "Salary Sacrifice")
        self.assertIn("salary_sacrifice", breakdown.inputs)
        self.assertEqual(breakdown.inputs["salary_sacrifice"], 5000)
        labels = {step.label for step in breakdown.steps}
        self.assertNotIn("Employer Pension (3%)", labels)
        self.assertNotIn("Pension Contribution", labels)
        self.assertNotIn("ER NI Saved to SIPP", labels)

    def test_salary_sacrifice_reduces_tax_and_ni(self):
        """A sacrifice of £15k on £300/day reduces IT and NI; pension is skipped."""
        no_sac = InsideIR35Calculator.calculate(300, 240, 25)
        with_sac = InsideIR35Calculator.calculate(300, 240, 25, salary_sacrifice=15000)

        assert with_sac.income_tax is not None
        assert no_sac.income_tax is not None
        assert with_sac.employee_ni is not None
        assert no_sac.employee_ni is not None
        assert with_sac.pension is not None
        assert no_sac.pension is not None
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
        assert breakdown.pension is not None
        self.assertEqual(breakdown.pension.employee_contribution, 0)
        self.assertEqual(breakdown.pension.employer_contribution, 0)
        self.assertFalse(breakdown.pension.eligible)
        labels = {step.label for step in breakdown.steps}
        self.assertNotIn("Employer Pension (3%)", labels)
        self.assertNotIn("Pension Contribution", labels)

    def test_salary_sacrifice_er_ni_saving_computed(self):
        """With sacrifice through PayStream, ER NI saving is positive and stored."""
        breakdown = InsideIR35Calculator.calculate(
            500, 240, 25, salary_sacrifice=5000, is_paystream=True
        )
        self.assertIn("er_ni_saving", breakdown.inputs)
        self.assertGreater(breakdown.inputs["er_ni_saving"], 0)

    def test_salary_sacrifice_budget_round_trip(self):
        """PayStream net-pay: budget = gross + er_ni + levy within ±1 rounding."""
        from payday.constants import APPRENTICESHIP_LEVY_RATE

        for rate, sacrifice in [(300, 5000), (500, 15000), (800, 10000)]:
            breakdown = InsideIR35Calculator.calculate(
                rate, 240, 25, salary_sacrifice=sacrifice, is_paystream=True
            )
            gross = self._find_step(breakdown, "Gross Salary").amount
            weeks = 240 / 5
            admin_charge = round(8.40 * weeks)
            sac_budget = rate * 240 - sacrifice - round(25 * 240 / 5) - admin_charge
            assert breakdown.employer_ni is not None
            actual = (
                gross
                + breakdown.employer_ni.total_er_ni
                + round(gross * APPRENTICESHIP_LEVY_RATE)
            )
            self.assertAlmostEqual(actual, sac_budget, delta=1)

    # ── is_paystream (PayStream umbrella) tests ─────────────────────────

    def test_paystream_backward_compatible_default(self):
        """Default (is_paystream=False) is identical to not passing it."""
        default = InsideIR35Calculator.calculate(500, 240, 25, salary_sacrifice=5000)
        explicit = InsideIR35Calculator.calculate(
            500, 240, 25, salary_sacrifice=5000, is_paystream=False
        )
        self.assertEqual(default.annual_take_home, explicit.annual_take_home)
        self.assertEqual(default.steps, explicit.steps)
        self.assertNotIn("is_paystream", default.inputs)

    def test_generic_sacrifice_direct_reduction(self):
        """Generic umbrella: gross = baseline gross − sacrifice (saving retained)."""
        no_sac = InsideIR35Calculator.calculate(500, 240, 25)
        baseline_gross = self._find_step(no_sac, "Gross Salary").amount
        breakdown = InsideIR35Calculator.calculate(500, 240, 25, salary_sacrifice=5000)
        gross = self._find_step(breakdown, "Gross Salary").amount
        self.assertEqual(gross, baseline_gross - 5000)
        self.assertNotIn("er_ni_saving", breakdown.inputs)

    def test_generic_sacrifice_umbrella_retains_saving(self):
        """Generic take-home must be lower than the PayStream net-pay take-home."""
        generic = InsideIR35Calculator.calculate(500, 240, 25, salary_sacrifice=5000)
        paystream = InsideIR35Calculator.calculate(
            500, 240, 25, salary_sacrifice=5000, is_paystream=True
        )
        self.assertLess(generic.annual_take_home, paystream.annual_take_home)

    def test_paystream_explicit_er_ni_saving_line(self):
        """PayStream waterfall shows the ER NI saving passed back as a line."""
        breakdown = InsideIR35Calculator.calculate(
            500, 240, 25, salary_sacrifice=5000, is_paystream=True
        )
        saving = self._find_step(breakdown, "Employer NI saving (passed back)")
        self.assertGreater(saving.amount, 0)
        self.assertIn("er_ni_saving", breakdown.inputs)
        self.assertEqual(breakdown.inputs["er_ni_saving"], saving.amount)

    def test_paystream_waterfall_balances_to_gross(self):
        """PayStream: Assignment − S − M − admin − ref ER NI + saving − levy = gross."""
        breakdown = InsideIR35Calculator.calculate(
            500, 240, 25, salary_sacrifice=5000, is_paystream=True
        )
        gross = self._find_step(breakdown, "Gross Salary").amount
        assignment = self._find_step(breakdown, "Assignment Rate").amount
        sacrifice = -self._find_step(breakdown, "Salary Sacrifice").amount
        margin = -self._find_step(breakdown, "Umbrella Margin").amount
        admin = -self._find_step(breakdown, "PayStream Admin Charge").amount
        er_ni = -self._find_step(breakdown, "Employer NI (15%)").amount
        saving = self._find_step(breakdown, "Employer NI saving (passed back)").amount
        levy = -self._find_step(breakdown, "Apprenticeship Levy (0.5%)").amount
        self.assertEqual(
            assignment - sacrifice - margin - admin - er_ni + saving - levy, gross
        )
        self.assertGreater(admin, 0)

    def test_paystream_admin_charge_only_when_sacrificing(self):
        """No admin charge without a salary sacrifice."""
        breakdown = InsideIR35Calculator.calculate(500, 240, 25, is_paystream=True)
        self.assertNotIn("admin_charge", breakdown.inputs)
        labels = {step.label for step in breakdown.steps}
        self.assertNotIn("PayStream Admin Charge", labels)

    def test_paystream_admin_charge_recorded(self):
        """With sacrifice, PayStream admin charge is recorded in inputs."""
        breakdown = InsideIR35Calculator.calculate(
            500, 240, 25, salary_sacrifice=5000, is_paystream=True
        )
        weeks = 240 / 5
        self.assertIn("admin_charge", breakdown.inputs)
        self.assertEqual(breakdown.inputs["admin_charge"], round(8.40 * weeks))

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
        assert breakdown.income_tax is not None
        assert without.income_tax is not None
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

        assert breakdown.income_tax is not None
        self.assertLess(breakdown.income_tax.personal_allowance, 12570)
        self.assertTrue(breakdown.income_tax.tapered)

        without = InsideIR35Calculator.calculate(600, 240, 25, start_month=8)
        assert without.income_tax is not None
        self.assertFalse(without.income_tax.tapered)

    def test_existing_dividends_not_consuming_rate_bands(self):
        """Dividends should not consume PAYE rate bands; tax must be lower."""
        mixed = InsideIR35Calculator.calculate(
            200, 240, 25, start_month=8, existing_income=16000, existing_dividends=15000
        )
        buggy = InsideIR35Calculator.calculate(
            200, 240, 25, start_month=8, existing_income=31000
        )
        self.assertIn("existing_dividends", mixed.inputs)
        self.assertEqual(mixed.inputs["existing_dividends"], 15000)
        assert mixed.income_tax is not None
        assert buggy.income_tax is not None
        self.assertLess(mixed.income_tax.total_tax, buggy.income_tax.total_tax)

    def test_existing_dividends_affect_pa_tapering(self):
        """High dividends trigger PA taper even when employment income is low."""
        breakdown = InsideIR35Calculator.calculate(
            600,
            240,
            25,
            start_month=8,
            existing_income=10000,
            existing_dividends=200000,
        )
        assert breakdown.income_tax is not None
        self.assertEqual(breakdown.income_tax.personal_allowance, 0)
        self.assertTrue(breakdown.income_tax.tapered)

    def test_existing_income_float_stored(self):
        """Float existing_income should be stored and used correctly."""
        breakdown = InsideIR35Calculator.calculate(
            500, 240, 25, start_month=8, existing_income=30000.50
        )
        self.assertIn("existing_income", breakdown.inputs)
        self.assertEqual(breakdown.inputs["existing_income"], 30000.50)
        self.assertGreater(breakdown.annual_take_home, 0)

    def test_existing_dividends_float_stored(self):
        """Float existing_dividends should be stored and used correctly."""
        breakdown = InsideIR35Calculator.calculate(
            500, 240, 25, start_month=8, existing_dividends=15000.75
        )
        self.assertIn("existing_dividends", breakdown.inputs)
        self.assertEqual(breakdown.inputs["existing_dividends"], 15000.75)
        self.assertGreater(breakdown.annual_take_home, 0)

    # ── Year Taxable Income tests ──────────────────────────────────────

    def test_year_taxable_income_full_year(self):
        """Full year: year_taxable_income equals effective_gross."""
        breakdown = InsideIR35Calculator.calculate(500, 240, 25)
        gross = self._find_step(breakdown, "Gross Salary").amount
        self.assertEqual(breakdown.year_taxable_income, gross)
        step = self._find_step(breakdown, "Year Taxable Income")
        self.assertEqual(step.amount, gross)
        self.assertTrue(step.is_subtotal)

    def test_year_taxable_income_partial_year_no_existing(self):
        """Partial year with no existing income: equals gross."""
        breakdown = InsideIR35Calculator.calculate(500, 240, 25, start_month=8)
        gross = self._find_step(breakdown, "Gross Salary").amount
        self.assertEqual(breakdown.year_taxable_income, gross)
        step = self._find_step(breakdown, "Year Taxable Income")
        self.assertEqual(step.amount, gross)

    def test_year_taxable_income_partial_year_with_existing(self):
        """Partial year with existing income and dividends: gross + existing."""
        breakdown = InsideIR35Calculator.calculate(
            500,
            240,
            25,
            start_month=8,
            existing_income=30000,
            existing_dividends=15000,
        )
        gross = self._find_step(breakdown, "Gross Salary").amount
        expected = gross + 30000 + 15000
        self.assertEqual(breakdown.year_taxable_income, expected)
        step = self._find_step(breakdown, "Year Taxable Income")
        self.assertEqual(step.amount, expected)

    def test_year_taxable_income_with_salary_sacrifice(self):
        """Salary sacrifice reduces effective_gross, so year taxable
        income reflects the reduced gross."""
        breakdown = InsideIR35Calculator.calculate(
            500,
            240,
            25,
            salary_sacrifice=5000,
        )
        gross = self._find_step(breakdown, "Gross Salary").amount
        self.assertEqual(breakdown.year_taxable_income, gross)

    def test_effective_days_on_partial_year(self):
        """effective_days=170 overrides the pro-rated 160 for an Aug start."""
        breakdown = InsideIR35Calculator.calculate(
            500, 240, 25, start_month=8, effective_days=170
        )
        self.assertEqual(breakdown.inputs["effective_working_days"], 170)
        self.assertEqual(self._find_step(breakdown, "Assignment Rate").amount, 85000)
        expected_display = round(breakdown.annual_take_home / 170 * 20)
        self.assertEqual(breakdown.display_take_home, expected_display)

    def test_effective_days_on_full_year(self):
        """effective_days=252 on full year overrides working_days=240."""
        breakdown = InsideIR35Calculator.calculate(500, 240, 25, effective_days=252)
        self.assertEqual(self._find_step(breakdown, "Assignment Rate").amount, 126000)

    def test_effective_days_defaults_to_none(self):
        """Omitting effective_days keeps old pro-rate behavior."""
        default = InsideIR35Calculator.calculate(500, 240, 25, start_month=8)
        explicit_none = InsideIR35Calculator.calculate(
            500, 240, 25, start_month=8, effective_days=None
        )
        self.assertEqual(default.annual_take_home, explicit_none.annual_take_home)
        self.assertEqual(
            default.inputs["effective_working_days"],
            explicit_none.inputs["effective_working_days"],
        )

    # ── region (Scotland) integration tests ────────────────────────────

    def test_scotland_region_changes_income_tax(self):
        # Same gross, different IT. Use a fixed assignment to keep gross stable.
        scot = InsideIR35Calculator.calculate(500, 240, 25, region="scotland")
        ruk = InsideIR35Calculator.calculate(500, 240, 25, region="rest_of_uk")
        assert scot.income_tax is not None
        assert ruk.income_tax is not None
        self.assertEqual(scot.income_tax.region, "scotland")
        self.assertEqual(ruk.income_tax.region, "rest_of_uk")
        # Scotland tax diverges from rUK (for this gross/tapered-PA case it's higher)
        self.assertNotEqual(scot.income_tax.total_tax, ruk.income_tax.total_tax)
        # Verify against direct calc_income_tax on the same gross/PA
        from payday.income_tax import calc_personal_allowance, calc_income_tax

        gross = self._find_step(ruk, "Gross Salary").amount
        pa, _ = calc_personal_allowance(gross)
        self.assertEqual(
            scot.income_tax.total_tax,
            calc_income_tax(gross, pa, region="scotland").total_tax,
        )
        self.assertEqual(scot.inputs.get("region"), "scotland")

    def test_scotland_region_stored_only_for_scotland(self):
        scot = InsideIR35Calculator.calculate(500, 240, 25, region="scotland")
        self.assertEqual(scot.inputs.get("region"), "scotland")
        for alias in (None, "rest_of_uk", "england", "wales", "northern_ireland"):
            ruk = InsideIR35Calculator.calculate(500, 240, 25, region=alias)
            self.assertNotEqual(ruk.inputs.get("region"), "scotland")
            assert ruk.income_tax is not None
            self.assertEqual(ruk.income_tax.region, "rest_of_uk")


if __name__ == "__main__":
    unittest.main()
