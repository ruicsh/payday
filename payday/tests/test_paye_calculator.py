import unittest
from payday.calculators.paye import PAYECalculator


class TestPAYECalculator(unittest.TestCase):
    def _find_step(self, breakdown, label):
        """Helper to find a step by its label."""
        for step in breakdown.steps:
            if step.label == label:
                return step
        self.fail(f"Step with label '{label}' not found in breakdown")

    def test_calculate_50k(self):
        # £50,000 salary
        breakdown = PAYECalculator.calculate(50000)

        self.assertEqual(breakdown.mode, "PAYE")

        # Verify step labels
        self.assertEqual(
            self._find_step(breakdown, "Annual Gross Salary").amount, 50000
        )
        self.assertEqual(
            self._find_step(breakdown, "Personal Allowance").amount, -12570
        )
        self.assertGreater(self._find_step(breakdown, "Taxable Income").amount, 0)
        self.assertLess(self._find_step(breakdown, "Income Tax").amount, 0)
        self.assertLess(self._find_step(breakdown, "National Insurance").amount, 0)
        self.assertLess(self._find_step(breakdown, "Pension Contribution").amount, 0)
        self.assertGreater(self._find_step(breakdown, "Annual Take-Home").amount, 0)
        self.assertGreater(self._find_step(breakdown, "Monthly Take-Home").amount, 0)

        # Pro-rata check
        self.assertEqual(breakdown.display_take_home, breakdown.annual_take_home // 12)
        self.assertEqual(
            breakdown.display_take_home,
            self._find_step(breakdown, "Monthly Take-Home").amount,
        )

    def test_calculate_tapered_pa(self):
        # £125,140 salary — ANI is reduced by the relief-at-source pension
        # (G=2,202 for 125,140), so PA is 1101, not 0.
        breakdown = PAYECalculator.calculate(125140)

        self.assertEqual(
            self._find_step(breakdown, "Personal Allowance (tapered)").amount, -1101
        )
        # Taxable = salary − remaining PA (RAS keeps full salary taxable)
        self.assertEqual(self._find_step(breakdown, "Taxable Income").amount, 124039)

    def test_calculate_pension_trigger(self):
        # £30,000 salary - above trigger (£10,000)
        breakdown = PAYECalculator.calculate(30000)
        self.assertLess(self._find_step(breakdown, "Pension Contribution").amount, 0)

    # ── salary_sacrifice tests ─────────────────────────────────────────

    def test_salary_sacrifice_backward_compatible_default(self):
        """Calling with salary_sacrifice=0 should match default."""
        default = PAYECalculator.calculate(50000)
        explicit = PAYECalculator.calculate(50000, salary_sacrifice=0)
        self.assertEqual(default.annual_take_home, explicit.annual_take_home)
        self.assertEqual(default.steps, explicit.steps)

    def test_salary_sacrifice_adds_waterfall_steps(self):
        """With a sacrifice, the waterfall shows Salary Sacrifice and Adjusted Gross Salary."""
        breakdown = PAYECalculator.calculate(50000, salary_sacrifice=5000)
        self._find_step(breakdown, "Salary Sacrifice")
        self._find_step(breakdown, "Adjusted Gross Salary")

    def test_salary_sacrifice_reduces_tax_and_ni(self):
        """A sacrifice of £5k on £50k reduces IT and NI; pension is skipped."""
        no_sac = PAYECalculator.calculate(50000)
        with_sac = PAYECalculator.calculate(50000, salary_sacrifice=5000)

        assert with_sac.income_tax is not None
        assert no_sac.income_tax is not None
        assert with_sac.employee_ni is not None
        assert no_sac.employee_ni is not None
        assert with_sac.pension is not None
        self.assertLess(with_sac.income_tax.total_tax, no_sac.income_tax.total_tax)
        self.assertLess(with_sac.employee_ni.total_ni, no_sac.employee_ni.total_ni)
        self.assertEqual(with_sac.pension.employee_contribution, 0)

    def test_salary_sacrifice_take_home_savings(self):
        """£5k sacrifice should reduce take-home by less than £5k due to tax/NI savings."""
        no_sac = PAYECalculator.calculate(50000)
        with_sac = PAYECalculator.calculate(50000, salary_sacrifice=5000)

        reduction = no_sac.annual_take_home - with_sac.annual_take_home
        self.assertGreater(reduction, 0)
        self.assertLess(reduction, 5000)

    def test_salary_sacrifice_exact_amounts(self):
        """Verify exact take-home for £50k salary with £5k sacrifice."""
        breakdown = PAYECalculator.calculate(50000, salary_sacrifice=5000)

        self.assertEqual(
            self._find_step(breakdown, "Annual Gross Salary").amount, 50000
        )
        self.assertEqual(self._find_step(breakdown, "Salary Sacrifice").amount, -5000)
        self.assertEqual(
            self._find_step(breakdown, "Adjusted Gross Salary").amount, 45000
        )

    def test_salary_sacrifice_skips_auto_enrolment(self):
        """With sacrifice, auto-enrolment pension is skipped entirely."""
        breakdown = PAYECalculator.calculate(50000, salary_sacrifice=5000)
        assert breakdown.pension is not None
        self.assertEqual(breakdown.pension.employee_contribution, 0)
        self.assertFalse(breakdown.pension.eligible)
        labels = {step.label for step in breakdown.steps}
        self.assertNotIn("Pension Contribution", labels)

    # ── region (Scotland) integration tests ────────────────────────────

    def test_scotland_region_changes_income_tax(self):
        scot = PAYECalculator.calculate(50000, region="scotland")
        ruk = PAYECalculator.calculate(50000, region="rest_of_uk")
        assert scot.income_tax is not None
        assert ruk.income_tax is not None
        # 50k: G=2,188 auto-enrolment. RAS extends the basic band (rUK still
        # within basic → 7486 unchanged; Scotland intermediate extends → 8523)
        self.assertEqual(scot.income_tax.total_tax, 8523)
        self.assertEqual(ruk.income_tax.total_tax, 7486)
        self.assertEqual(scot.income_tax.region, "scotland")
        self.assertEqual(ruk.income_tax.region, "rest_of_uk")
        # Scotland take-home is lower due to higher tax
        self.assertLess(scot.annual_take_home, ruk.annual_take_home)

    def test_scotland_region_stored_in_inputs(self):
        scot = PAYECalculator.calculate(50000, region="scotland")
        self.assertEqual(scot.inputs.get("region"), "scotland")
        # rUK (explicit alias or None) does not set region key — formatter checks == "scotland"
        for alias in (None, "rest_of_uk", "england", "wales", "northern_ireland"):
            ruk = PAYECalculator.calculate(50000, region=alias)
            self.assertNotEqual(ruk.inputs.get("region"), "scotland")
            assert ruk.income_tax is not None
            self.assertEqual(ruk.income_tax.region, "rest_of_uk")

    # ── pension_method (relief at source vs net pay) ─────────────────

    def test_pension_method_default_is_relief_at_source(self):
        default = PAYECalculator.calculate(50000)
        ras = PAYECalculator.calculate(50000, pension_method="relief_at_source")
        assert default.income_tax is not None
        assert ras.income_tax is not None
        self.assertEqual(default.annual_take_home, ras.annual_take_home)
        self.assertEqual(default.income_tax.total_tax, ras.income_tax.total_tax)
        self.assertNotIn("pension_method", default.inputs)

    def test_pension_method_net_pay_stored_in_inputs(self):
        net = PAYECalculator.calculate(50000, pension_method="net_pay")
        self.assertEqual(net.inputs.get("pension_method"), "net_pay")

    def test_pension_method_invalid_raises(self):
        with self.assertRaises(ValueError):
            PAYECalculator.calculate(50000, pension_method="bogus")

    def test_pension_method_deduction_and_taxable(self):
        # 50k: G=2,188, net=1,750. Net-pay deducts full G, RAS deducts 80%.
        # Net-pay taxable = 47,812; RAS taxable = 50,000 with band extension.
        net = PAYECalculator.calculate(50000, pension_method="net_pay")
        ras = PAYECalculator.calculate(50000, pension_method="relief_at_source")
        assert net.income_tax is not None
        assert ras.income_tax is not None
        self.assertEqual(net.income_tax.taxable_income, 35242)
        self.assertEqual(ras.income_tax.taxable_income, 37430)
        self.assertEqual(self._find_step(net, "Pension Contribution").amount, -2188)
        self.assertEqual(self._find_step(ras, "Pension Contribution").amount, -1750)

    def test_pension_method_basic_rate_take_home_equal(self):
        # At basic rate both methods give same take-home (20% relief either way)
        net = PAYECalculator.calculate(50000, pension_method="net_pay")
        ras = PAYECalculator.calculate(50000, pension_method="relief_at_source")
        self.assertEqual(net.annual_take_home, ras.annual_take_home)

    def test_pension_method_higher_rate_take_home_equal_ruk(self):
        # At higher rate rUK: net-pay saves 40% on G vs RAS 20% provider + 20% extension
        net = PAYECalculator.calculate(80000, pension_method="net_pay")
        ras = PAYECalculator.calculate(80000, pension_method="relief_at_source")
        self.assertEqual(net.annual_take_home, ras.annual_take_home)

    def test_pension_method_sacrifice_ignores_method(self):
        # With sacrifice workplace pension is disabled regardless of method
        net = PAYECalculator.calculate(
            50000, salary_sacrifice=5000, pension_method="net_pay"
        )
        ras = PAYECalculator.calculate(
            50000, salary_sacrifice=5000, pension_method="relief_at_source"
        )
        assert net.pension is not None
        assert ras.pension is not None
        self.assertEqual(net.pension.employee_contribution, 0)
        self.assertEqual(ras.pension.employee_contribution, 0)
        self.assertEqual(net.annual_take_home, ras.annual_take_home)

    def test_annual_allowance_threshold_subtracts_pension(self):
        # AA threshold = total income − gross employee contribution (both methods)
        # For 300k: qualifying capped at 44,030 → G=2,202 → threshold 297,798
        b_ras = PAYECalculator.calculate(300000, pension_method="relief_at_source")
        b_net = PAYECalculator.calculate(300000, pension_method="net_pay")
        assert b_ras.annual_allowance is not None
        assert b_net.annual_allowance is not None
        # Both methods share the same threshold/adjusted (display when tapered)
        self.assertEqual(
            b_ras.annual_allowance.threshold_income,
            b_net.annual_allowance.threshold_income,
        )


if __name__ == "__main__":
    unittest.main()
