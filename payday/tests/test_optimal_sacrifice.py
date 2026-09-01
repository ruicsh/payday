import unittest
from payday.calculators.optimal_sacrifice import (
    calc_optimal_sacrifice_paye,
    calc_optimal_sacrifice_inside_ir35,
    inverse_solve_gross_salary,
)
from payday.calculators.inside_ir35 import InsideIR35Calculator


class TestInverseSolveGrossSalary(unittest.TestCase):
    def test_inverse_no_pension_below_5000(self):
        """Target gross <= 5000: budget = target * 1.005."""
        budget = inverse_solve_gross_salary(4000, include_er_pension=False)
        self.assertEqual(budget, round(4000 * 1.005))

    def test_inverse_no_pension_above_5000(self):
        """Target gross > 5000: budget = target * 1.155 - 750."""
        budget = inverse_solve_gross_salary(6000, include_er_pension=False)
        self.assertEqual(budget, round(6000 * 1.155 - 750))

    def test_inverse_round_trip_no_pension_low(self):
        """Round-trip: solve_gross_salary(inverse(target)) ≈ target (low)."""
        for target in [0, 2500, 5000]:
            budget = inverse_solve_gross_salary(target, include_er_pension=False)
            gross = InsideIR35Calculator.solve_gross_salary(
                budget, include_er_pension=False
            )
            self.assertEqual(gross, target)

    def test_inverse_round_trip_no_pension_mid(self):
        """Round-trip: solve_gross_salary(inverse(target)) ≈ target (mid)."""
        for target in [6000, 15000, 50000, 100000]:
            budget = inverse_solve_gross_salary(target, include_er_pension=False)
            gross = InsideIR35Calculator.solve_gross_salary(
                budget, include_er_pension=False
            )
            self.assertEqual(gross, target)

    def test_inverse_include_pension_below_5000(self):
        """With pension, target gross <= 5000: budget = target * 1.005."""
        budget = inverse_solve_gross_salary(4000, include_er_pension=True)
        self.assertEqual(budget, round(4000 * 1.005))

    def test_inverse_include_pension_between_5001_and_10000(self):
        """5000 < target <= 10000: no pension trigger, budget = target * 1.155 - 750."""
        budget = inverse_solve_gross_salary(8000, include_er_pension=True)
        self.assertEqual(budget, round(8000 * 1.155 - 750))

    def test_inverse_include_pension_between_10001_and_50270(self):
        """10000 < target <= 50270: budget = target * 1.185 - 937.20."""
        budget = inverse_solve_gross_salary(30000, include_er_pension=True)
        self.assertEqual(budget, round(30000 * 1.185 - 937.20))

    def test_inverse_include_pension_above_50270(self):
        """target > 50270: budget = target * 1.155 + 570.90."""
        budget = inverse_solve_gross_salary(60000, include_er_pension=True)
        self.assertEqual(budget, round(60000 * 1.155 + 570.90))

    def test_inverse_round_trip_with_pension(self):
        """Round-trip with pension enabled."""
        for target in [4000, 8000, 25000, 60000]:
            budget = inverse_solve_gross_salary(target, include_er_pension=True)
            gross = InsideIR35Calculator.solve_gross_salary(
                budget, include_er_pension=True
            )
            self.assertEqual(gross, target)


class TestCalcOptimalSacrificePAYE(unittest.TestCase):
    def test_150k_gross_at_100k_cap(self):
        """150k gross with 100k cap → sacrifice 50k to avoid taper."""
        result = calc_optimal_sacrifice_paye(150_000, cap=100_000)
        self.assertEqual(result, 50_000)

    def test_90k_gross_at_100k_cap(self):
        """90k is already below 100k cap → no sacrifice needed."""
        result = calc_optimal_sacrifice_paye(90_000, cap=100_000)
        self.assertEqual(result, 0)

    def test_100k_gross_at_100k_cap(self):
        """Exactly at cap → no sacrifice needed."""
        result = calc_optimal_sacrifice_paye(100_000, cap=100_000)
        self.assertEqual(result, 0)

    def test_custom_cap_80k(self):
        """130k gross with 80k cap → sacrifice 50k."""
        result = calc_optimal_sacrifice_paye(130_000, cap=80_000)
        self.assertEqual(result, 50_000)

    def test_gross_at_zero(self):
        """0 gross → 0 sacrifice."""
        result = calc_optimal_sacrifice_paye(0, cap=100_000)
        self.assertEqual(result, 0)

    def test_gross_below_cap_by_large_margin(self):
        """50k gross with 100k cap → no sacrifice needed."""
        result = calc_optimal_sacrifice_paye(50_000, cap=100_000)
        self.assertEqual(result, 0)

    def test_default_cap_is_100k(self):
        """Default cap should be 100,000."""
        from inspect import signature

        sig = signature(calc_optimal_sacrifice_paye)
        self.assertEqual(sig.parameters["cap"].default, 100_000)

    def test_sacrifice_capped_at_60k(self):
        """Gross well above cap → sacrifice capped at £60k/year."""
        result = calc_optimal_sacrifice_paye(300_000, cap=100_000)
        self.assertEqual(result, 60_000)

    def test_sacrifice_below_60k_is_not_capped(self):
        """Sacrifice under £60k is returned as-is."""
        result = calc_optimal_sacrifice_paye(150_000, cap=100_000)
        self.assertEqual(result, 50_000)

    def test_other_income_included_in_paye_target(self):
        """PAYE ANI is gross - sacrifice + other; other pushes target down."""
        # 75k salary + 10k other, cap 60k → need 25k sacrifice to hit 60k ANI
        result = calc_optimal_sacrifice_paye(75_000, cap=60_000, other_income=10_000)
        self.assertEqual(result, 25_000)

    def test_other_income_breaches_cap_gives_zero(self):
        """Other income alone >= cap → can't fix with sacrifice."""
        result = calc_optimal_sacrifice_paye(50_000, cap=60_000, other_income=70_000)
        self.assertEqual(result, 0)


class TestCalcOptimalSacrificeInsideIR35(unittest.TestCase):
    def test_below_cap_returns_zero(self):
        """If effective_gross is already within cap, return 0."""
        # £200/day, 240 days, £25/week margin
        # assignment = 48000, margin = 1200 → budget ≈ 46800
        # gross ≈ (46800+750)/1.155 ≈ 41169 → ANI = 41169 < 100000
        result = calc_optimal_sacrifice_inside_ir35(48000, 1200, cap=100_000)
        self.assertEqual(result, 0)

    def test_above_cap_returns_calculated_sacrifice(self):
        """£600/day, 240 days, £25/wk margin, 100k cap."""
        # assignment = 144000, margin = 1200
        # target_gross = 100000 (no existing income)
        # target_budget = 100000 * 1.155 - 750 = 114750
        # sacrifice = 144000 - 114750 - 1200 = 28050
        result = calc_optimal_sacrifice_inside_ir35(144_000, 1200, cap=100_000)
        self.assertEqual(result, 28_050)

    def test_existing_income_reduces_sacrifice_needed(self):
        """Existing income reduces the target gross, so less sacrifice needed."""
        # £600/day, 240 days, £25/wk margin, 100k cap, 20k existing
        # target_gross = 100000 - 20000 = 80000
        # target_budget = 80000 * 1.155 - 750 = 91650
        # sacrifice = 144000 - 91650 - 1200 = 51150
        result = calc_optimal_sacrifice_inside_ir35(
            144_000, 1200, cap=100_000, existing_income=20_000
        )
        self.assertEqual(result, 51_150)

    def test_existing_income_exceeds_cap(self):
        """Existing income > cap → can't fix with sacrifice, return 0."""
        result = calc_optimal_sacrifice_inside_ir35(
            144_000, 1200, cap=100_000, existing_income=120_000
        )
        self.assertEqual(result, 0)

    def test_custom_cap(self):
        """£600/day, 240 days, 25 margin, 80k cap."""
        # target_gross = 80000
        # target_budget = 80000 * 1.155 - 750 = 91650
        # sacrifice = 144000 - 91650 - 1200 = 51150
        result = calc_optimal_sacrifice_inside_ir35(144_000, 1200, cap=80_000)
        self.assertEqual(result, 51_150)

    def test_sacrifice_clamped_to_max_feasible(self):
        """When target budget pushes sacrifice beyond budget, clamp it."""
        # Very low cap → sacrifice tries to exceed budget, clamp
        result = calc_optimal_sacrifice_inside_ir35(50_000, 500, cap=1_000)
        # budget = 50000 - 500 = 49500
        # max feasible = 49500 - 1 = 49499
        # But target_gross = 1000, so budget = 1000*1.005 = 1005
        # sacrifice = 50000 - 1005 - 500 = 48495 < 49499, so it's fine
        max_feasible = 50_000 - 500 - 1
        self.assertLessEqual(result, max_feasible)
        self.assertGreaterEqual(result, 0)

    def test_default_cap_is_100k(self):
        """Default cap should be 100,000."""
        from inspect import signature

        sig = signature(calc_optimal_sacrifice_inside_ir35)
        self.assertEqual(sig.parameters["cap"].default, 100_000)

    def test_other_income_reduces_target_inside(self):
        """Other income is part of ANI; it reduces target gross like existing."""
        # 144k assignment, 1200 margin, 100k cap, 10k other
        # target_gross = 90k → budget 103200 → sacrifice 39600
        result = calc_optimal_sacrifice_inside_ir35(
            144_000, 1200, cap=100_000, other_income=10_000
        )
        self.assertEqual(result, 39_600)

    def test_sacrifice_capped_at_60k(self):
        """Very high assignment → sacrifice capped at £60k."""
        result = calc_optimal_sacrifice_inside_ir35(1_000_000, 0, cap=100_000)
        self.assertEqual(result, 60_000)


if __name__ == "__main__":
    unittest.main()
