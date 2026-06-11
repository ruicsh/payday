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
        self.assertEqual(self._find_step(breakdown, "Annual Gross Salary").amount, 50000)
        self.assertEqual(self._find_step(breakdown, "Personal Allowance").amount, -12570)
        self.assertGreater(self._find_step(breakdown, "Taxable Income").amount, 0)
        self.assertLess(self._find_step(breakdown, "Income Tax").amount, 0)
        self.assertLess(self._find_step(breakdown, "National Insurance").amount, 0)
        self.assertLess(self._find_step(breakdown, "Pension Contribution").amount, 0)
        self.assertGreater(self._find_step(breakdown, "Annual Take-Home").amount, 0)
        self.assertGreater(self._find_step(breakdown, "Monthly Take-Home").amount, 0)

        # Pro-rata check
        self.assertEqual(breakdown.display_take_home, breakdown.annual_take_home // 12)
        self.assertEqual(breakdown.display_take_home, self._find_step(breakdown, "Monthly Take-Home").amount)

    def test_calculate_tapered_pa(self):
        # £125,140 salary - PA should be 0 and label should be tapered
        breakdown = PAYECalculator.calculate(125140)
        
        self.assertEqual(self._find_step(breakdown, "Personal Allowance (tapered)").amount, 0)
        self.assertEqual(self._find_step(breakdown, "Taxable Income").amount, 125140)

    def test_calculate_pension_trigger(self):
        # £30,000 salary - above trigger (£10,000)
        breakdown = PAYECalculator.calculate(30000)
        self.assertLess(self._find_step(breakdown, "Pension Contribution").amount, 0)

if __name__ == "__main__":
    unittest.main()
