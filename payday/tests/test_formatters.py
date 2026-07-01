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

    def test_float_rounded_to_nearest_pound(self):
        self.assertEqual(format_gbp(30000.51), "£30,001")
        self.assertEqual(format_gbp(30000.49), "£30,000")


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

    def test_format_outside_ir35_extra_info(self):
        steps = [
            StepLine("Company Revenue", 120000),
            StepLine("Take-Home", 80000, is_subtotal=True),
        ]
        breakdown = SalaryBreakdown(
            mode="Outside IR35",
            inputs={"day_rate": 500, "working_days": 240},
            steps=steps,
            annual_take_home=80000,
            display_take_home=6667,
        )
        output = format_breakdown(breakdown)
        self.assertIn("Outside IR35 (Ltd Co)", output)
        self.assertIn("(Salary: £12,570", output)
        self.assertIn("Dividends: £67,430)", output)
        self.assertIn("(£500/day × 240 days)", output)

    def test_format_inside_ir35_day_rate_context(self):
        steps = [
            StepLine("Assignment Rate", 120000),
            StepLine("Annual Take-Home", 70000),
        ]
        breakdown = SalaryBreakdown(
            mode="Inside IR35",
            inputs={"day_rate": 500, "working_days": 240, "margin_weekly": 25},
            steps=steps,
            annual_take_home=70000,
            display_take_home=5833,
        )
        output = format_breakdown(breakdown)
        self.assertIn("Inside IR35 (Umbrella)", output)
        self.assertIn("(£500/day × 240 days)", output)

    def test_mode_title_fallback(self):
        breakdown = SalaryBreakdown(
            mode="Unknown Mode",
            inputs={},
            steps=[],
            annual_take_home=0,
            display_take_home=0,
        )
        output = format_breakdown(breakdown)
        self.assertIn("Unknown Mode — 2026/27", output)

    def test_partial_year_title_includes_period(self):
        steps = [
            StepLine("Assignment Rate", 80000),
            StepLine("Annual Take-Home", 47840),
        ]
        breakdown = SalaryBreakdown(
            mode="Inside IR35",
            inputs={
                "day_rate": 500,
                "working_days": 240,
                "margin_weekly": 25,
                "contract_period": "Aug 2026–Apr 2027 (8 months)",
                "effective_working_days": 160,
            },
            steps=steps,
            annual_take_home=47840,
            display_take_home=5980,
        )
        output = format_breakdown(breakdown)
        self.assertIn("Inside IR35 (Umbrella)", output)
        self.assertIn("Aug 2026–Apr 2027 (8 months)", output)

    def test_partial_year_day_rate_context(self):
        steps = [
            StepLine("Assignment Rate", 80000),
            StepLine("Annual Take-Home", 47840),
        ]
        breakdown = SalaryBreakdown(
            mode="Inside IR35",
            inputs={
                "day_rate": 500,
                "working_days": 240,
                "margin_weekly": 25,
                "contract_period": "Aug 2026–Apr 2027 (8 months)",
                "effective_working_days": 160,
            },
            steps=steps,
            annual_take_home=47840,
            display_take_home=5980,
        )
        output = format_breakdown(breakdown)
        # Shows pro-rated days instead of full-year days
        self.assertIn("× 160 days, Aug 2026–Apr 2027", output)
        self.assertNotIn("× 240 days", output)

    def test_partial_year_shows_existing_income(self):
        steps = [
            StepLine("Assignment Rate", 80000),
            StepLine("Annual Take-Home", 47840),
        ]
        breakdown = SalaryBreakdown(
            mode="Inside IR35",
            inputs={
                "day_rate": 500,
                "working_days": 240,
                "margin_weekly": 25,
                "contract_period": "Aug 2026–Apr 2027 (8 months)",
                "effective_working_days": 160,
                "existing_income": 30000,
            },
            steps=steps,
            annual_take_home=47840,
            display_take_home=5980,
        )
        output = format_breakdown(breakdown)
        self.assertIn("[existing: £30,000]", output)


if __name__ == "__main__":
    unittest.main()
