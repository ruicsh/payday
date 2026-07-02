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
        # £125,140 salary - PA should be 0 and label should be tapered
        breakdown = PAYECalculator.calculate(125140)

        self.assertEqual(
            self._find_step(breakdown, "Personal Allowance (tapered)").amount, 0
        )
        self.assertEqual(self._find_step(breakdown, "Taxable Income").amount, 125140)

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
        self.assertEqual(breakdown.pension.employee_contribution, 0)
        self.assertFalse(breakdown.pension.eligible)
        labels = {step.label for step in breakdown.steps}
        self.assertNotIn("Pension Contribution", labels)


if __name__ == "__main__":
    unittest.main()
