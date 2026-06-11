import unittest
from payday.models import SalaryBreakdown, StepLine
from payday.formatters import format_gbp, format_breakdown


class TestFormatGbp(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(format_gbp(50000), "£50,000")

    def test_negative(self):
        self.assertEqual(format_gbp(-3421), "-£3,421")

    def test_small_number(self):
        self.assertEqual(format_gbp(12570), "£12,570")

    def test_zero(self):
        self.assertEqual(format_gbp(0), "£0")

    def test_large_number(self):
        self.assertEqual(format_gbp(1000000), "£1,000,000")


class TestFormatBreakdown(unittest.TestCase):
    def test_paye_format_basic(self):
        steps = [
            StepLine("Annual Gross Salary", 50000),
            StepLine("Personal Allowance", -12570, indent=1),
            StepLine("Taxable Income", 37430, indent=1),
            StepLine("Income Tax", -7486, indent=1),
            StepLine("National Insurance", -2994, indent=1, is_subtotal=True),
            StepLine("Annual Take-Home", 39520),
            StepLine("Monthly Take-Home", 3293),
        ]
        breakdown = SalaryBreakdown(
            mode="PAYE",
            inputs={"salary": 50000},
            steps=steps,
            annual_take_home=39520,
            display_take_home=3293,
        )
        output = format_breakdown(breakdown)
        self.assertIn("PAYE", output)
        self.assertIn("£50,000", output)
        self.assertIn("£39,520", output)
        self.assertIn("£3,293", output)
        self.assertIn("2026/27", output)

    def test_format_contains_waterfall_lines(self):
        steps = [
            StepLine("Annual Gross Salary", 50000),
            StepLine("Taxable Income", 37430, indent=1),
            StepLine("Income Tax", -7486, indent=1, is_subtotal=True),
            StepLine("Annual Take-Home", 39520),
        ]
        breakdown = SalaryBreakdown(
            mode="PAYE",
            inputs={"salary": 50000},
            steps=steps,
            annual_take_home=39520,
            display_take_home=3293,
        )
        output = format_breakdown(breakdown)
        # Should contain separator line
        self.assertIn("──", output)


if __name__ == "__main__":
    unittest.main()
