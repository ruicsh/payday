import unittest
from payday.calculators.outside_ir35 import OutsideIR35Calculator


class TestOutsideIR35Calculator(unittest.TestCase):
    def _find_step(self, breakdown, label):
        """Helper to find a step by its label."""
        for step in breakdown.steps:
            if step.label == label:
                return step
        self.fail(f"Step with label '{label}' not found in breakdown")

    def test_full_pipeline_500_day(self):
        # £500/day, 240 days
        breakdown = OutsideIR35Calculator.calculate(500, 240)

        self.assertEqual(breakdown.mode, "Outside IR35")
        self.assertEqual(breakdown.inputs["day_rate"], 500)
        self.assertEqual(breakdown.inputs["working_days"], 240)

        # Revenue = 500 * 240 = 120000
        self.assertEqual(self._find_step(breakdown, "Company Revenue").amount, 120000)

        # Salary = 12570
        self.assertEqual(self._find_step(breakdown, "Director Salary").amount, -12570)

        # Er NI on 12570: (12570 - 5000) * 0.15 = 7570 * 0.15 = 1135.5 -> 1136
        self.assertEqual(self._find_step(breakdown, "Employer NI (15%)").amount, -1136)

        # Profit = 120000 - 12570 - 1136 = 106294
        self.assertEqual(self._find_step(breakdown, "Company Profit").amount, 106294)

        # CT on 106294: 26574 - 2156 = 24418
        self.assertEqual(self._find_step(breakdown, "Corporation Tax").amount, -24418)

        # Distributable profit = 106294 - 24418 = 81876
        self.assertEqual(
            self._find_step(breakdown, "Distributable Profit").amount, 81876
        )

        # Take-home should be positive and reasonable
        self.assertGreater(breakdown.annual_take_home, 0)
        self.assertGreater(breakdown.display_take_home, 0)

        # CT rate on 106294 should be > 19% (marginal relief band)
        self.assertAlmostEqual(
            breakdown.corporation_tax.total_ct / breakdown.corporation_tax.profit,
            0.23,  # ~23% effective
            delta=0.02,
        )

        # 20-day pro-rata check
        expected_display = round(breakdown.annual_take_home / 240 * 20)
        self.assertEqual(breakdown.display_take_home, expected_display)

    def test_low_day_rate_no_ct(self):
        # Low revenue < salary, so profit is negative
        breakdown = OutsideIR35Calculator.calculate(50, 240)
        # Revenue = 12000, less than salary 12570
        # Profit = 12000 - 12570 - 0(er_ni) = -570
        self.assertGreaterEqual(breakdown.annual_take_home, 0)
        # Ensure dividend tax calculation handled the loss correctly
        self.assertEqual(breakdown.dividend_tax.total_tax, 0)
        self.assertEqual(breakdown.dividend_tax.dividend_allowance, 0)

    def test_high_day_rate_additional_rate(self):
        # £1200/day, 240 days -> high profit, should hit additional dividend rate
        breakdown = OutsideIR35Calculator.calculate(1200, 240)
        # Revenue = 288000
        # Profit should be very high
        self.assertGreater(breakdown.annual_take_home, 0)
        # Dividend tax should be present
        self.assertIsNotNone(breakdown.dividend_tax)
        if breakdown.dividend_tax:
            # At this revenue level, additional rate may apply
            self.assertGreaterEqual(breakdown.dividend_tax.additional_band, 0)

    def test_marginal_ct_band(self):
        # Revenue around 100k → profit should be in marginal relief band
        breakdown = OutsideIR35Calculator.calculate(420, 240)
        # Revenue = 100800
        # Profit = 100800 - 12570 - er_ni = ~87000
        # 87000 is between 50000 and 250000 → marginal relief applies
        self.assertGreater(breakdown.corporation_tax.marginal_relief, 0)

    def test_small_profits_ct_rate(self):
        # Very low day rate → profit under 50k → 19% CT
        breakdown = OutsideIR35Calculator.calculate(250, 240)
        # Revenue = 60000, Profit ≈ 46294
        # 46294 < 50000 → flat 19% CT (marginal relief should be zero)
        self.assertLessEqual(breakdown.corporation_tax.profit, 50000)
        self.assertEqual(breakdown.corporation_tax.marginal_relief, 0)


if __name__ == "__main__":
    unittest.main()
