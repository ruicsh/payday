import unittest
from payday.annual_allowance import (
    calc_adjusted_income,
    calc_annual_allowance,
    calc_threshold_income,
    find_max_pension_for_funcs,
    find_max_pension_for_threshold,
    find_max_pension_sole_trader,
)
from payday.calculators.inside_ir35 import InsideIR35Calculator, paystream_max_pension
from payday.calculators.outside_ir35 import OutsideIR35Calculator
from payday.calculators.paye import PAYECalculator
from payday.calculators.sole_trader import SoleTraderCalculator
from payday.constants import AA_TAPER_MIN, ANNUAL_ALLOWANCE


class TestCalcAnnualAllowance(unittest.TestCase):
    def test_no_taper_both_below(self):
        res = calc_annual_allowance(150_000, 150_000)
        self.assertEqual(res.annual_allowance, 60_000)
        self.assertFalse(res.tapered)
        self.assertEqual(res.threshold_income, 150_000)
        self.assertEqual(res.adjusted_income, 150_000)

    def test_no_taper_threshold_low_adjusted_high(self):
        # Threshold <=200k => no taper even if adjusted is very high.
        res = calc_annual_allowance(150_000, 300_000)
        self.assertEqual(res.annual_allowance, 60_000)
        self.assertFalse(res.tapered)

    def test_no_taper_adjusted_low_threshold_high(self):
        res = calc_annual_allowance(300_000, 200_000)
        self.assertEqual(res.annual_allowance, 60_000)
        self.assertFalse(res.tapered)

    def test_no_taper_exact_boundaries(self):
        # Exactly at 200k / 260k => no taper (strict >).
        res = calc_annual_allowance(200_000, 260_000)
        self.assertEqual(res.annual_allowance, 60_000)
        self.assertFalse(res.tapered)
        res = calc_annual_allowance(200_000, 500_000)
        self.assertEqual(res.annual_allowance, 60_000)
        self.assertFalse(res.tapered)
        res = calc_annual_allowance(500_000, 260_000)
        self.assertEqual(res.annual_allowance, 60_000)
        self.assertFalse(res.tapered)

    def test_taper_one_pound_over(self):
        # 200_001 / 260_001 => reduction int(1*0.5)=0 => still 60k but tapered.
        res = calc_annual_allowance(200_001, 260_001)
        self.assertEqual(res.annual_allowance, 60_000)
        self.assertTrue(res.tapered)

    def test_taper_small_reduction(self):
        # 210k / 270k => reduction 5k => 55k
        res = calc_annual_allowance(210_000, 270_000)
        self.assertEqual(res.annual_allowance, 55_000)
        self.assertTrue(res.tapered)

    def test_taper_mid(self):
        # 210k / 280k => reduction 10k => 50k
        res = calc_annual_allowance(210_000, 280_000)
        self.assertEqual(res.annual_allowance, 50_000)

    def test_taper_odd_adjusted(self):
        # 210k / 261k => reduction int(1000*0.5)=500 => 59500
        res = calc_annual_allowance(210_000, 261_000)
        self.assertEqual(res.annual_allowance, 59_500)

    def test_taper_high(self):
        # 300k / 360k => reduction 50k => 10k floor
        res = calc_annual_allowance(300_000, 360_000)
        self.assertEqual(res.annual_allowance, 10_000)
        self.assertTrue(res.tapered)

    def test_taper_floor(self):
        # 360k / 400k => reduction 70k => 60k-70k = -10k => floor 10k
        res = calc_annual_allowance(360_000, 400_000)
        self.assertEqual(res.annual_allowance, AA_TAPER_MIN)

    def test_taper_float_inputs(self):
        res = calc_annual_allowance(210_000.4, 270_000.6)
        # Both rounded before calc
        self.assertEqual(res.threshold_income, 210_000)
        self.assertEqual(res.adjusted_income, 270_001)

    def test_doctest_examples(self):
        self.assertEqual(
            calc_annual_allowance(150_000, 150_000).annual_allowance, 60_000
        )
        self.assertEqual(
            calc_annual_allowance(150_000, 300_000).annual_allowance, 60_000
        )
        self.assertEqual(
            calc_annual_allowance(210_000, 260_000).annual_allowance, 60_000
        )
        self.assertEqual(
            calc_annual_allowance(210_000, 270_000).annual_allowance, 55_000
        )
        self.assertEqual(
            calc_annual_allowance(300_000, 360_000).annual_allowance, 10_000
        )
        self.assertEqual(
            calc_annual_allowance(360_000, 400_000).annual_allowance, 10_000
        )


class TestCalcThresholdAndAdjusted(unittest.TestCase):
    def test_threshold_no_extras(self):
        self.assertEqual(calc_threshold_income(300_000), 300_000)

    def test_threshold_with_sacrifice(self):
        self.assertEqual(
            calc_threshold_income(300_000, salary_sacrifice=60_000), 360_000
        )

    def test_threshold_with_relief(self):
        # 300k - 10k*1.25 = 287500
        self.assertEqual(
            calc_threshold_income(300_000, relief_at_source_pension=10_000), 287_500
        )

    def test_threshold_with_both(self):
        # 300k + 20k - 10k*1.25 = 307500
        self.assertEqual(
            calc_threshold_income(
                300_000, salary_sacrifice=20_000, relief_at_source_pension=10_000
            ),
            307_500,
        )

    def test_threshold_relief_zero(self):
        self.assertEqual(
            calc_threshold_income(100_000, relief_at_source_pension=0), 100_000
        )

    def test_adjusted_no_pension(self):
        self.assertEqual(calc_adjusted_income(300_000, 0), 300_000)

    def test_adjusted_with_pension(self):
        self.assertEqual(calc_adjusted_income(300_000, 60_000), 360_000)

    def test_adjusted_float(self):
        self.assertEqual(calc_adjusted_income(300_000.4, 10_000.6), 310_001)


class TestFindMaxPension(unittest.TestCase):
    def test_no_taper_threshold_low(self):
        self.assertEqual(find_max_pension_for_threshold(150_000), 60_000)
        self.assertEqual(find_max_pension_for_threshold(200_000), 60_000)

    def test_taper_returns_within_allowance(self):
        for thr in [210_000, 250_000, 300_000, 340_000, 360_000, 400_000]:
            max_p = find_max_pension_for_threshold(thr)
            # max_p must be <= AA at that pension
            adjusted = thr + max_p
            aa = calc_annual_allowance(thr, adjusted).annual_allowance
            self.assertLessEqual(max_p, aa, f"thr {thr} max {max_p} > aa {aa}")
            # And max_p+1 must exceed AA (unless already at 60k cap)
            if max_p < ANNUAL_ALLOWANCE:
                adjusted_next = thr + max_p + 1
                aa_next = calc_annual_allowance(thr, adjusted_next).annual_allowance
                self.assertGreater(
                    max_p + 1, aa_next, f"thr {thr} max+1 {max_p + 1} <= aa {aa_next}"
                )

    def test_specific_threshold_210k(self):
        max_p = find_max_pension_for_threshold(210_000)
        # 210k threshold: max should be 56k-57k range; verify property not exact hardcode
        self.assertGreaterEqual(max_p, 55_000)
        self.assertLessEqual(max_p, 60_000)

    def test_specific_threshold_300k(self):
        max_p = find_max_pension_for_threshold(300_000)
        # thr 300k => adjusted 326667 at 26667 pension => AA 26667
        self.assertGreaterEqual(max_p, 20_000)
        self.assertLessEqual(max_p, 30_000)
        # Verify exact with current implementation
        self.assertEqual(max_p, 26_667)

    def test_floor_at_high_threshold(self):
        max_p = find_max_pension_for_threshold(360_000)
        self.assertEqual(max_p, 10_000)
        max_p = find_max_pension_for_threshold(400_000)
        self.assertEqual(max_p, 10_000)

    def test_custom_adjusted(self):
        # Custom: adjusted = threshold + pension//2
        def half_adjusted(p):
            return 210_000 + p // 2

        max_p = find_max_pension_for_threshold(
            210_000, get_adjusted_for_pension=half_adjusted
        )
        # Should be larger than default since adjusted grows slower
        default_max = find_max_pension_for_threshold(210_000)
        self.assertGreaterEqual(max_p, default_max)

    def test_custom_adjusted_no_taper(self):
        # If adjusted never exceeds 260k, max is 60k
        def capped_adjusted(p):
            return 200_000  # always below

        max_p = find_max_pension_for_threshold(
            300_000, get_adjusted_for_pension=capped_adjusted
        )
        self.assertEqual(max_p, 60_000)


class TestFindMaxPensionForFuncs(unittest.TestCase):
    def test_monotonic_simple(self):
        # Simple monotonic: thr constant 250k, adj=thr+p
        def thr(p):
            return 250_000

        def adj(p):
            return 250_000 + p

        max_p = find_max_pension_for_funcs(thr, adj, cap=60_000)
        # Brute force check
        brute = max(
            p for p in range(60_001) if p <= calc_annual_allowance(thr(p), adj(p)).annual_allowance
        )
        self.assertEqual(max_p, brute)
        self.assertEqual(max_p, 43_333)

    def test_paystream_1500x240(self):
        # Regression: PayStream at £1500×240 previously allowed 23282 > 21322 (illegal).
        # Correct cap is ~22031 and must be ≤ AA.
        from payday.constants import PAYSTREAM_ADMIN_CHARGE_WEEKLY

        assignment = 1500 * 240
        weeks = 240 / 5
        annual_margin = round(25 * weeks)
        admin = round(PAYSTREAM_ADMIN_CHARGE_WEEKLY * weeks)
        # Use canonical helper — same logic as calculator
        max_p = paystream_max_pension(
            assignment, annual_margin, admin, cap=60_000
        )
        # Brute via paystream thr/adj functions
        from payday.calculators.inside_ir35 import InsideIR35Calculator

        def thr(p):
            sac_budget = assignment - p - annual_margin - admin
            if sac_budget < 0:
                sac_budget = 0
            g = InsideIR35Calculator.solve_gross_salary(sac_budget, include_er_pension=False)
            return round(g + p)

        def adj(p):
            return thr(p) + p

        brute = max(p for p in range(60_001) if p <= calc_annual_allowance(thr(p), adj(p)).annual_allowance)
        self.assertEqual(max_p, brute)
        # Must be tapered and under floor
        self.assertLess(max_p, 60_000)
        aa = calc_annual_allowance(thr(max_p), adj(max_p)).annual_allowance
        self.assertLessEqual(max_p, aa)
        self.assertGreaterEqual(max_p, 20_000)

    def test_outside_1500x240_brute_match(self):
        # Outside at £1500×240 was under-capped 46355 vs true 47871 (single recursion).
        from payday.corporation_tax import calc_corporation_tax
        from payday.national_insurance import calc_employer_ni
        from payday.constants import PERSONAL_ALLOWANCE

        salary = PERSONAL_ALLOWANCE
        er_ni = calc_employer_ni(salary).total_er_ni
        revenue = 1500 * 240

        def thr(p):
            prof = revenue - salary - er_ni - p
            if prof <= 0:
                divs = 0
            else:
                ct = calc_corporation_tax(prof).total_ct
                divs = prof - ct
            return round(salary + divs)

        def adj(p):
            return thr(p) + p

        max_p = find_max_pension_for_funcs(thr, adj, cap=60_000)
        brute = max(p for p in range(60_001) if p <= calc_annual_allowance(thr(p), adj(p)).annual_allowance)
        self.assertEqual(max_p, brute)
        self.assertEqual(max_p, 47_871)

    def test_cap_respected(self):
        def thr(p):
            return 300_000

        def adj(p):
            return 360_000  # constant high → AA 10000

        self.assertEqual(find_max_pension_for_funcs(thr, adj, cap=5_000), 5_000)
        self.assertEqual(find_max_pension_for_funcs(thr, adj, cap=20_000), 10_000)


class TestFindMaxPensionSoleTrader(unittest.TestCase):
    def _brute(self, total, cap=60_000):
        return max(
            p for p in range(cap + 1) if p <= calc_annual_allowance(total - round(p * 1.25), total).annual_allowance
        )

    def test_no_taper_below_260k(self):
        for total in [200_000, 250_000, 260_000]:
            self.assertEqual(find_max_pension_sole_trader(total, cap=60_000), 60_000)
            self.assertEqual(find_max_pension_sole_trader(total, cap=60_000), self._brute(total))

    def test_nonmonotonic_band(self):
        # Band where large pension removes taper — previously under-capped 52500 vs 60000.
        for total in [271_000, 272_000, 273_000, 274_000, 275_000]:
            with self.subTest(total=total):
                self.assertEqual(find_max_pension_sole_trader(total, cap=60_000), 60_000)
                self.assertEqual(find_max_pension_sole_trader(total, cap=60_000), self._brute(total))

    def test_permanently_tapered(self):
        # Never drops below 200k within cap → AA floor
        self.assertEqual(find_max_pension_sole_trader(360_000, cap=60_000), 10_000)
        self.assertEqual(find_max_pension_sole_trader(360_000, cap=60_000), self._brute(360_000))
        self.assertEqual(find_max_pension_sole_trader(310_000, cap=60_000), 35_000)
        self.assertEqual(find_max_pension_sole_trader(310_000, cap=60_000), self._brute(310_000))

    def test_cap_below_p_cross(self):
        # total 275k, cap 40000 < p_cross 60000 → only tapered regime, should be min(cap, AA_tapered)
        # AA_tapered at total 275k = 52500, so with cap 40000 expect 40000; with cap 60000 expect 60000
        self.assertEqual(find_max_pension_sole_trader(275_000, cap=40_000), 40_000)
        self.assertEqual(find_max_pension_sole_trader(275_000, cap=52_000), 52_000)
        # cap 55k >52500 but <60000 cross → still capped to AA_tapered 52500
        self.assertEqual(find_max_pension_sole_trader(275_000, cap=55_000), 52_500)
        self.assertEqual(find_max_pension_sole_trader(275_000, cap=55_000), self._brute(275_000, cap=55_000))

    def test_brute_match_sweep(self):
        for total in list(range(0, 500_000, 25_000)) + [205_000, 261_000, 275_000, 310_000]:
            with self.subTest(total=total):
                self.assertEqual(find_max_pension_sole_trader(total, cap=60_000), self._brute(total))
                self.assertEqual(find_max_pension_sole_trader(total, cap=30_000), self._brute(total, cap=30_000))


class TestAnnualAllowanceIntegrationPAYE(unittest.TestCase):
    def _find_step(self, breakdown, label):
        for s in breakdown.steps:
            if s.label == label:
                return s
        self.fail(f"missing step {label}")

    def test_other_income_affects_pa_taper(self):
        # Salary 90k + other 20k => ANI 110k => PA tapered
        no_other = PAYECalculator.calculate(90_000, other_income=0)
        with_other = PAYECalculator.calculate(90_000, other_income=20_000)
        assert no_other.income_tax is not None
        assert with_other.income_tax is not None
        self.assertFalse(no_other.income_tax.tapered)
        self.assertTrue(with_other.income_tax.tapered)
        self.assertIn("other_income", with_other.inputs)

    def test_other_income_in_year_taxable(self):
        b = PAYECalculator.calculate(50_000, other_income=15_000)
        self.assertEqual(b.year_taxable_income, 65_000)
        b2 = PAYECalculator.calculate(50_000, other_income=0)
        self.assertEqual(b2.year_taxable_income, 50_000)

    def test_paye_no_taper_low_income(self):
        b = PAYECalculator.calculate(150_000, salary_sacrifice=50_000, other_income=0)
        assert b.annual_allowance is not None
        self.assertFalse(b.annual_allowance.tapered)
        self.assertEqual(b.inputs["salary_sacrifice"], 50_000)
        # No AA line when not tapered
        labels = [s.label for s in b.steps]
        self.assertNotIn("Annual Allowance (tapered to £60,000)", labels)

    def test_paye_taper_caps_sacrifice(self):
        # Salary 300k => threshold 300k => max 26667, 60k should be capped
        b = PAYECalculator.calculate(300_000, salary_sacrifice=60_000, other_income=0)
        assert b.annual_allowance is not None
        self.assertTrue(b.annual_allowance.tapered)
        self.assertEqual(b.annual_allowance.annual_allowance, 26_667)
        self.assertEqual(b.inputs["salary_sacrifice"], 26_667)
        self.assertEqual(b.inputs["annual_allowance"], 26_667)
        self.assertEqual(b.inputs["threshold_income"], 300_000)
        # AA line appears
        self._find_step(b, "Annual Allowance (tapered to £26,667)")

    def test_paye_taper_via_other_income(self):
        # Salary 250k + other 50k => threshold 300k => same cap
        b = PAYECalculator.calculate(
            250_000, salary_sacrifice=60_000, other_income=50_000
        )
        assert b.annual_allowance is not None
        self.assertTrue(b.annual_allowance.tapered)
        self.assertEqual(b.inputs["salary_sacrifice"], 26_667)

    def test_paye_taper_boundary(self):
        # Threshold 210k (e.g. salary 210k) + sacrifice 50k => adjusted 260k => no taper, so 60k not capped
        # Salary 210k threshold 210k, max 56k+, so 50k stays
        b = PAYECalculator.calculate(210_000, salary_sacrifice=50_000, other_income=0)
        self.assertEqual(b.inputs["salary_sacrifice"], 50_000)
        # But 60k would be capped
        b2 = PAYECalculator.calculate(210_000, salary_sacrifice=60_000, other_income=0)
        self.assertLess(b2.inputs["salary_sacrifice"], 60_000)
        assert b2.annual_allowance is not None
        self.assertTrue(b2.annual_allowance.tapered)


class TestAnnualAllowanceIntegrationInsideIR35(unittest.TestCase):
    def _find_step(self, breakdown, label):
        for s in breakdown.steps:
            if s.label == label:
                return s
        self.fail(f"missing {label}")

    def test_other_income_taper(self):
        # Low day rate no taper; with large other_income cap
        low = InsideIR35Calculator.calculate(
            500, 240, salary_sacrifice=30_000, other_income=0
        )
        assert low.annual_allowance is not None
        self.assertFalse(low.annual_allowance.tapered)
        high = InsideIR35Calculator.calculate(
            500, 240, salary_sacrifice=60_000, other_income=150_000
        )
        assert high.annual_allowance is not None
        self.assertTrue(high.annual_allowance.tapered)
        self.assertLess(high.inputs["salary_sacrifice"], 60_000)
        self.assertIn("other_income", high.inputs)

    def test_year_taxable_includes_other(self):
        b = InsideIR35Calculator.calculate(500, 240, other_income=20_000)
        b2 = InsideIR35Calculator.calculate(500, 240, other_income=0)
        assert b.year_taxable_income is not None
        assert b2.year_taxable_income is not None
        self.assertEqual(b.year_taxable_income, b2.year_taxable_income + 20_000)

    def test_taper_caps_sacrifice(self):
        # High day rate 1200 => gross ~247k, threshold ~247k => tapered
        b = InsideIR35Calculator.calculate(
            1200, 240, salary_sacrifice=60_000, other_income=0
        )
        assert b.annual_allowance is not None
        self.assertTrue(b.annual_allowance.tapered)
        self.assertLess(b.inputs["salary_sacrifice"], 60_000)


class TestAnnualAllowanceIntegrationOutsideIR35(unittest.TestCase):
    def test_other_income_and_taper(self):
        # 500*240 revenue ~120k, dividends ~70k, total ~82k <200k no taper
        no_taper = OutsideIR35Calculator.calculate(
            500, 240, director_pension=50_000, other_income=0
        )
        assert no_taper.annual_allowance is not None
        self.assertFalse(no_taper.annual_allowance.tapered)
        self.assertEqual(no_taper.inputs["director_pension"], 50_000)
        # With large other_income push over threshold
        tapered = OutsideIR35Calculator.calculate(
            800, 240, director_pension=60_000, other_income=150_000
        )
        assert tapered.annual_allowance is not None
        self.assertTrue(tapered.annual_allowance.tapered)
        self.assertLess(tapered.inputs["director_pension"], 60_000)
        self.assertIn("other_income", tapered.inputs)
        self.assertIn("annual_allowance", tapered.inputs)

    def test_year_taxable_includes_other(self):
        b = OutsideIR35Calculator.calculate(500, 240, other_income=25_000)
        b2 = OutsideIR35Calculator.calculate(500, 240, other_income=0)
        assert b.year_taxable_income is not None
        assert b2.year_taxable_income is not None
        self.assertEqual(b.year_taxable_income, b2.year_taxable_income + 25_000)

    def test_pension_not_capped_when_below(self):
        b = OutsideIR35Calculator.calculate(
            500, 240, director_pension=10_000, other_income=0
        )
        self.assertEqual(b.inputs["director_pension"], 10_000)


class TestAnnualAllowanceIntegrationSoleTrader(unittest.TestCase):
    def test_other_income_and_taper(self):
        # 500*240 turnover 120k, trading 120k <200k no taper
        no_taper = SoleTraderCalculator.calculate(
            500, 240, personal_pension=20_000, other_income=0
        )
        assert no_taper.annual_allowance is not None
        self.assertFalse(no_taper.annual_allowance.tapered)
        # With other income 100k, total 220k, pension 60k threshold 220-75=145 => but adjusted 220 >260? No, 220<260 so no taper
        # Need larger: 800*240=192k +100k=292k => adjusted 292>260 and threshold with 60k => 217k >200 => taper
        tapered = SoleTraderCalculator.calculate(
            800, 240, personal_pension=60_000, other_income=100_000
        )
        assert tapered.annual_allowance is not None
        self.assertTrue(tapered.annual_allowance.tapered)
        self.assertLess(tapered.inputs["personal_pension"], 60_000)

    def test_year_taxable_includes_other(self):
        b = SoleTraderCalculator.calculate(500, 240, other_income=30_000)
        b2 = SoleTraderCalculator.calculate(500, 240, other_income=0)
        assert b.year_taxable_income is not None
        assert b2.year_taxable_income is not None
        self.assertEqual(b.year_taxable_income, b2.year_taxable_income + 30_000)

    def test_high_profit_capped_to_floor(self):
        # 1500*240=360k turnover, total 360k => AA floor 10k
        b = SoleTraderCalculator.calculate(
            1500, 240, personal_pension=60_000, other_income=0
        )
        assert b.annual_allowance is not None
        self.assertTrue(b.annual_allowance.tapered)
        self.assertEqual(b.inputs["personal_pension"], 10_000)
        self.assertEqual(b.inputs["annual_allowance"], 10_000)

    def test_relief_can_avoid_taper(self):
        # Total 250k: threshold without pension 250k >200k, adjusted 250k <260k => no taper, but with pension 60k threshold 175k => no taper
        # So pension 60k should not be capped when total <260k even though threshold >200k?
        # Actually adjusted 250k <260k => no taper, so 60k stays
        b = SoleTraderCalculator.calculate(
            1000, 240, personal_pension=60_000, other_income=10_000
        )
        # 1000*240=240k +10k=250k => adjusted 250k <260k => no taper
        assert b.annual_allowance is not None
        self.assertFalse(b.annual_allowance.tapered)
        self.assertEqual(b.inputs["personal_pension"], 60_000)


if __name__ == "__main__":
    unittest.main()
