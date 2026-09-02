import json
import os
import tempfile
import unittest
from io import StringIO
from unittest.mock import patch

from payday.calculators.inside_ir35 import InsideIR35Calculator
from payday.calculators.outside_ir35 import OutsideIR35Calculator
from payday.calculators.paye import PAYECalculator
from payday.calculators.sole_trader import SoleTraderCalculator
from payday.config import load_config
from payday.constants import (
    CHILD_BENEFIT_ADDITIONAL_CHILD_WEEKLY,
    CHILD_BENEFIT_FIRST_CHILD_WEEKLY,
    HICBC_LOWER_THRESHOLD,
)
from payday.hicbc import (
    calc_hicbc,
    child_benefit_annual,
    hicbc_charge_rate,
    hicbc_effective_marginal_rate,
    recommended_ani_cap,
)


class TestChildBenefitAnnual(unittest.TestCase):
    def test_one_child(self):
        expected = int(CHILD_BENEFIT_FIRST_CHILD_WEEKLY * 52)
        self.assertEqual(child_benefit_annual(1), expected)
        self.assertEqual(child_benefit_annual(), expected)  # default 1

    def test_two_children(self):
        weekly = (
            CHILD_BENEFIT_FIRST_CHILD_WEEKLY + CHILD_BENEFIT_ADDITIONAL_CHILD_WEEKLY
        )
        self.assertEqual(child_benefit_annual(2), int(weekly * 52))

    def test_three_children(self):
        weekly = (
            CHILD_BENEFIT_FIRST_CHILD_WEEKLY + 2 * CHILD_BENEFIT_ADDITIONAL_CHILD_WEEKLY
        )
        self.assertEqual(child_benefit_annual(3), int(weekly * 52))

    def test_zero_children(self):
        self.assertEqual(child_benefit_annual(0), 0)

    def test_negative_children(self):
        self.assertEqual(child_benefit_annual(-1), 0)


class TestHICBCChargeRate(unittest.TestCase):
    def test_below_lower_threshold(self):
        for ani in [0, 30_000, 59_999, 60_000]:
            self.assertEqual(hicbc_charge_rate(ani), 0.0)

    def test_above_upper_threshold(self):
        for ani in [80_000, 80_001, 100_000, 150_000]:
            self.assertEqual(hicbc_charge_rate(ani), 1.0)

    def test_midpoint_70k(self):
        # 70k = 10k above 60k = 50 * £200 increments = 50%
        self.assertEqual(hicbc_charge_rate(70_000), 0.5)

    def test_quarter_points(self):
        # 65k = 25%, 75k = 75%
        self.assertEqual(hicbc_charge_rate(65_000), 0.25)
        self.assertEqual(hicbc_charge_rate(75_000), 0.75)

    def test_per_200_floor(self):
        # HMRC: 1% per *complete* £200 — floor, not round
        self.assertEqual(hicbc_charge_rate(60_100), 0.0)
        self.assertEqual(hicbc_charge_rate(60_199), 0.0)
        self.assertEqual(hicbc_charge_rate(60_200), 0.01)
        self.assertEqual(hicbc_charge_rate(60_300), 0.01)
        self.assertEqual(hicbc_charge_rate(60_399), 0.01)
        self.assertEqual(hicbc_charge_rate(60_400), 0.02)
        self.assertEqual(hicbc_charge_rate(78_300), 0.91)

    def test_75k_is_75_percent(self):
        # Issue example: £75k with child benefit -> 75% clawback
        self.assertEqual(hicbc_charge_rate(75_000), 0.75)


class TestCalcHICBC(unittest.TestCase):
    def test_no_charge_below_threshold(self):
        self.assertEqual(calc_hicbc(50_000), 0)
        self.assertEqual(calc_hicbc(60_000), 0)

    def test_full_charge_above_upper(self):
        annual = child_benefit_annual(1)
        self.assertEqual(calc_hicbc(90_000, annual), annual)
        self.assertEqual(calc_hicbc(80_000, annual), annual)

    def test_partial_charge_75k_one_child(self):
        annual = child_benefit_annual(1)
        # 75k = 75% -> floor(annual * 0.75)
        self.assertEqual(calc_hicbc(75_000, annual), int(annual * 0.75))

    def test_partial_charge_65k(self):
        annual = child_benefit_annual(1)
        self.assertEqual(calc_hicbc(65_000, annual), int(annual * 0.25))

    def test_charge_uses_floor(self):
        # 70k = 50% of 1355 would be 677.5 — floor gives 677, not 678
        # With int benefit 1354, 50% is exactly 677 — floor is unambiguous,
        # so use an explicit annual where .5 matters.
        self.assertEqual(calc_hicbc(70_000, 1355), 677)  # floor(677.5)
        self.assertEqual(calc_hicbc(65_000, 1355), 338)  # floor(338.75)

    def test_explicit_annual_overrides_num_children(self):
        self.assertEqual(calc_hicbc(70_000, 2000), 1000)  # 50% of 2000
        # num_children ignored when annual provided
        self.assertEqual(calc_hicbc(70_000, 2000, num_children=5), 1000)

    def test_num_children_scaling(self):
        annual2 = child_benefit_annual(2)
        self.assertEqual(calc_hicbc(70_000, num_children=2), int(annual2 * 0.5))

    def test_zero_benefit(self):
        self.assertEqual(calc_hicbc(75_000, 0), 0)


class TestHICBCEffectiveMarginal(unittest.TestCase):
    def test_one_child_60k_to_80k(self):
        annual = child_benefit_annual(1)
        rate = hicbc_effective_marginal_rate(60_000, 80_000, num_children=1)
        self.assertAlmostEqual(rate, annual / 20000, places=5)

    def test_two_children(self):
        annual2 = child_benefit_annual(2)
        rate = hicbc_effective_marginal_rate(60_000, 80_000, num_children=2)
        self.assertAlmostEqual(rate, annual2 / 20000, places=5)

    def test_same_ani_zero(self):
        self.assertEqual(hicbc_effective_marginal_rate(70_000, 70_000), 0.0)


class TestRecommendedANICap(unittest.TestCase):
    def test_without_child_benefit(self):
        self.assertEqual(recommended_ani_cap(False), 100_000)

    def test_with_child_benefit(self):
        self.assertEqual(recommended_ani_cap(True), HICBC_LOWER_THRESHOLD)


# ── Calculator integration ────────────────────────────────────────────


class TestPAYEHICBC(unittest.TestCase):
    def _has_child_benefit_line(self, breakdown):
        return any("Child Benefit (HICBC" in s.label for s in breakdown.steps)

    def test_no_flag_no_hicbc(self):
        b = PAYECalculator.calculate(75_000, has_child_benefit=False)
        self.assertIsNone(b.hicbc)
        self.assertFalse(self._has_child_benefit_line(b))
        self.assertNotIn("has_child_benefit", b.inputs)

    def test_below_threshold_zero_charge(self):
        b = PAYECalculator.calculate(55_000, has_child_benefit=True)
        assert b.hicbc is not None
        self.assertEqual(b.hicbc.charge, 0)
        self.assertEqual(b.hicbc.charge_rate, 0.0)
        self.assertEqual(b.hicbc.annual_benefit, child_benefit_annual(1))
        self.assertTrue(self._has_child_benefit_line(b))
        self.assertTrue(any("HICBC 0%" in s.label for s in b.steps))

    def test_75k_75_percent_clawback(self):
        # £75k salary with child benefit → ANI 72,798 after RAS pension
        # (G=2,202) → floor((72798-60000)/200)=63 → 63% clawback
        b = PAYECalculator.calculate(75_000, has_child_benefit=True)
        assert b.hicbc is not None
        self.assertEqual(b.hicbc.charge_rate, 0.63)
        self.assertEqual(b.hicbc.charge, int(child_benefit_annual(1) * 0.63))
        self.assertTrue(any("63%" in s.label for s in b.steps))
        self.assertIn("has_child_benefit", b.inputs)
        self.assertIn("hicbc_charge", b.inputs)

    def test_sacrifice_to_60k_clears_hicbc(self):
        b_before = PAYECalculator.calculate(75_000, has_child_benefit=True)
        b_after = PAYECalculator.calculate(
            75_000, salary_sacrifice=15_000, has_child_benefit=True
        )
        assert b_before.hicbc is not None
        assert b_after.hicbc is not None
        assert b_before.income_tax is not None
        assert b_after.income_tax is not None
        self.assertGreater(b_before.hicbc.charge, 0)
        self.assertEqual(b_after.hicbc.charge, 0)
        saved_it = b_before.income_tax.total_tax - b_after.income_tax.total_tax
        saved_hicbc = b_before.hicbc.charge - b_after.hicbc.charge
        # With RAS pension G=2,202, before ANI 72,798 (63% charge) vs
        # after sacrifice ANI 60,000 (0%). Saved IT now includes RAS band
        # extension, so 5,559 not 6,000.
        self.assertEqual(saved_it, 5559)
        self.assertEqual(saved_hicbc, int(child_benefit_annual(1) * 0.63))

    def test_60k_other_income_pushes_into_hicbc(self):
        # Salary 55k + 10k other = 65k gross; ANI 62,798 after RAS pension
        # (G=2,202) → floor((62798-60000)/200)=13 → 13% charge
        b = PAYECalculator.calculate(
            55_000, other_income=10_000, has_child_benefit=True
        )
        assert b.hicbc is not None
        self.assertEqual(b.hicbc.ani, 62_798)
        self.assertEqual(b.hicbc.charge_rate, 0.13)

    def test_100_percent_above_80k(self):
        b = PAYECalculator.calculate(85_000, has_child_benefit=True)
        assert b.hicbc is not None
        self.assertEqual(b.hicbc.charge_rate, 1.0)
        self.assertEqual(b.hicbc.charge, child_benefit_annual(1))
        self.assertTrue(any("100%" in s.label for s in b.steps))

    def test_floor_at_60199_still_zero(self):
        b = PAYECalculator.calculate(60_199, has_child_benefit=True)
        assert b.hicbc is not None
        self.assertEqual(b.hicbc.charge_rate, 0.0)
        self.assertEqual(b.hicbc.charge, 0)

    def test_floor_at_60300_is_one_percent(self):
        # 60,300 with RAS pension G=2,202 → ANI 58,098 (<60k) → 0%
        b = PAYECalculator.calculate(60_300, has_child_benefit=True)
        assert b.hicbc is not None
        self.assertEqual(b.hicbc.charge_rate, 0.0)

    def test_num_children_scales_benefit(self):
        b1 = PAYECalculator.calculate(75_000, has_child_benefit=True, num_children=1)
        b3 = PAYECalculator.calculate(75_000, has_child_benefit=True, num_children=3)
        assert b1.hicbc is not None
        assert b3.hicbc is not None
        self.assertEqual(b1.hicbc.annual_benefit, child_benefit_annual(1))
        self.assertEqual(b3.hicbc.annual_benefit, child_benefit_annual(3))
        # 75k → ANI 72,798 → 63% charge after RAS pension
        self.assertEqual(b3.hicbc.charge, int(child_benefit_annual(3) * 0.63))


class TestInsideIR35HICBC(unittest.TestCase):
    def _has_hicbc_line(self, b):
        return any("Child Benefit (HICBC" in s.label for s in b.steps)

    def test_no_flag_no_hicbc(self):
        b = InsideIR35Calculator.calculate(500, 240, 25, has_child_benefit=False)
        self.assertIsNone(b.hicbc)
        self.assertFalse(self._has_hicbc_line(b))

    def test_with_flag_has_hicbc(self):
        b = InsideIR35Calculator.calculate(500, 240, 25, has_child_benefit=True)
        self.assertIsNotNone(b.hicbc)
        self.assertTrue(self._has_hicbc_line(b))
        self.assertIn("has_child_benefit", b.inputs)

    def test_existing_income_feeds_ani(self):
        # Without existing, ANI from gross alone is around £60.8k (small
        # charge); with existing £30k it pushes ANI to ~£90.8k → 100% charge.
        b_without = InsideIR35Calculator.calculate(300, 240, 25, has_child_benefit=True)
        b_with = InsideIR35Calculator.calculate(
            300, 240, 25, existing_income=30_000, has_child_benefit=True
        )
        assert b_without.hicbc is not None
        assert b_with.hicbc is not None
        self.assertEqual(b_with.hicbc.charge_rate, 1.0)
        self.assertEqual(b_with.hicbc.charge, b_with.hicbc.annual_benefit)
        self.assertLess(b_without.hicbc.charge_rate, b_with.hicbc.charge_rate)


class TestOutsideSoleTraderHICBC(unittest.TestCase):
    def test_outside_has_hicbc_when_flag(self):
        b = OutsideIR35Calculator.calculate(500, 240, has_child_benefit=True)
        self.assertIsNotNone(b.hicbc)
        self.assertIn("has_child_benefit", b.inputs)

    def test_sole_trader_has_hicbc_when_flag(self):
        b = SoleTraderCalculator.calculate(500, 240, has_child_benefit=True)
        self.assertIsNotNone(b.hicbc)
        self.assertIn("has_child_benefit", b.inputs)

    def test_outside_no_flag_none(self):
        b = OutsideIR35Calculator.calculate(500, 240, has_child_benefit=False)
        self.assertIsNone(b.hicbc)

    def test_sole_no_flag_none(self):
        b = SoleTraderCalculator.calculate(500, 240, has_child_benefit=False)
        self.assertIsNone(b.hicbc)


# ── Optimal sacrifice with HICBC cap ──────────────────────────────────


class TestOptimalSacrificeWithHICBC(unittest.TestCase):
    def test_paye_75k_to_60k(self):
        from payday.calculators.optimal_sacrifice import calc_optimal_sacrifice_paye

        cap = recommended_ani_cap(True)  # 60k
        self.assertEqual(cap, 60_000)
        result = calc_optimal_sacrifice_paye(75_000, cap=cap)
        self.assertEqual(result, 15_000)

    def test_paye_75k_to_100k_no_sacrifice(self):
        from payday.calculators.optimal_sacrifice import calc_optimal_sacrifice_paye

        cap = recommended_ani_cap(False)  # 100k
        result = calc_optimal_sacrifice_paye(75_000, cap=cap)
        self.assertEqual(result, 0)

    def test_inside_75k_assignment_to_60k(self):
        from payday.calculators.optimal_sacrifice import (
            calc_optimal_sacrifice_inside_ir35,
        )

        # 75k assignment with 0 margin to 60k cap -> sacrifice = 75k - (60k*1.155-750) ≈ 6450
        result = calc_optimal_sacrifice_inside_ir35(75_000, 0, cap=60_000)
        expected = 75_000 - round(60_000 * 1.155 - 750)
        self.assertEqual(result, expected)


# ── Config ────────────────────────────────────────────────────────────


class TestConfigHasChildBenefit(unittest.TestCase):
    def _load(self, data):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            return load_config(path)
        finally:
            os.unlink(path)

    def test_true_accepted(self):
        cfg = self._load({"mode": "paye", "has_child_benefit": True})
        assert cfg is not None
        self.assertIs(cfg["has_child_benefit"], True)

    def test_false_accepted(self):
        cfg = self._load({"mode": "paye", "has_child_benefit": False})
        assert cfg is not None
        self.assertIs(cfg["has_child_benefit"], False)

    def test_null_accepted(self):
        cfg = self._load({"mode": "paye", "has_child_benefit": None})
        assert cfg is not None
        self.assertIsNone(cfg["has_child_benefit"])

    def test_absent_is_none(self):
        cfg = self._load({"mode": "paye"})
        assert cfg is not None
        self.assertIsNone(cfg["has_child_benefit"])

    def test_string_rejected(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"mode": "paye", "has_child_benefit": "yes"}, f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_int_rejected(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"mode": "paye", "has_child_benefit": 1}, f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)


class TestConfigNumChildren(unittest.TestCase):
    def _load(self, data):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            return load_config(path)
        finally:
            os.unlink(path)

    def test_valid_one(self):
        cfg = self._load({"mode": "paye", "num_children": 1})
        assert cfg is not None
        self.assertEqual(cfg["num_children"], 1)

    def test_valid_three(self):
        cfg = self._load({"mode": "paye", "num_children": 3})
        assert cfg is not None
        self.assertEqual(cfg["num_children"], 3)

    def test_true_is_default(self):
        cfg = self._load({"mode": "paye", "num_children": True})
        assert cfg is not None
        self.assertIs(cfg["num_children"], True)

    def test_null_accepted(self):
        cfg = self._load({"mode": "paye", "num_children": None})
        assert cfg is not None
        self.assertIsNone(cfg["num_children"])

    def test_zero_rejected(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"mode": "paye", "num_children": 0}, f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_negative_rejected(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"mode": "paye", "num_children": -1}, f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)


# ── CLI ───────────────────────────────────────────────────────────────


class TestCLIHICBC(unittest.TestCase):
    def test_prompt_has_child_benefit_config_true(self):
        from payday.cli import prompt_has_child_benefit

        with patch("sys.stdout", new_callable=StringIO):
            self.assertTrue(prompt_has_child_benefit({"has_child_benefit": True}))

    def test_prompt_has_child_benefit_config_false(self):
        from payday.cli import prompt_has_child_benefit

        with patch("sys.stdout", new_callable=StringIO):
            self.assertFalse(prompt_has_child_benefit({"has_child_benefit": False}))

    def test_prompt_has_child_benefit_config_absent_defaults_false(self):
        from payday.cli import prompt_has_child_benefit

        # Config present but flag absent → default False, no prompt
        with patch("sys.stdout", new_callable=StringIO):
            with patch("builtins.input") as mock_input:
                result = prompt_has_child_benefit({"mode": "paye"})
                mock_input.assert_not_called()
                self.assertFalse(result)

    @patch("builtins.input", return_value="y")
    def test_prompt_has_child_benefit_interactive_yes(self, _mock):
        from payday.cli import prompt_has_child_benefit

        self.assertTrue(prompt_has_child_benefit(None))

    @patch("builtins.input", return_value="n")
    def test_prompt_has_child_benefit_interactive_no(self, _mock):
        from payday.cli import prompt_has_child_benefit

        self.assertFalse(prompt_has_child_benefit(None))

    @patch("builtins.input", return_value="")
    def test_prompt_has_child_benefit_interactive_default_no(self, _mock):
        from payday.cli import prompt_has_child_benefit

        self.assertFalse(prompt_has_child_benefit(None))

    def test_prompt_num_children_config(self):
        from payday.cli import prompt_num_children

        with patch("sys.stdout", new_callable=StringIO):
            self.assertEqual(
                prompt_num_children({"num_children": 3}, has_child_benefit=True), 3
            )
            self.assertEqual(
                prompt_num_children({"num_children": True}, has_child_benefit=True), 1
            )
            # absent → default 1
            self.assertEqual(prompt_num_children({}, has_child_benefit=True), 1)
            # no child benefit → ignored, always 1
            self.assertEqual(
                prompt_num_children({"num_children": 3}, has_child_benefit=False), 1
            )

    def test_prompt_salary_sacrifice_uses_60k_when_child_benefit(self):
        from payday.cli import prompt_salary_sacrifice

        # PAYE 75k, has_child_benefit True, auto with cap=True should prompt with default 60k
        # Mock input "" to accept default 60k
        with patch("builtins.input", side_effect=[""]):
            with patch("sys.stdout", new_callable=StringIO):
                config = {
                    "salary_sacrifice_enabled": True,
                    "monthly_salary_sacrifice": "auto",
                    "income_target": True,
                    "has_child_benefit": True,
                }
                result = prompt_salary_sacrifice(
                    75_000, mode="paye", has_child_benefit=True, config=config
                )
                self.assertEqual(result, 15_000)
                self.assertEqual(result.frequency, "monthly")

    def test_prompt_salary_sacrifice_uses_100k_without_child_benefit(self):
        from payday.cli import prompt_salary_sacrifice

        with patch("builtins.input", side_effect=[""]):
            with patch("sys.stdout", new_callable=StringIO):
                config = {
                    "salary_sacrifice_enabled": True,
                    "monthly_salary_sacrifice": "auto",
                    "income_target": True,
                    "has_child_benefit": False,
                }
                result = prompt_salary_sacrifice(
                    75_000, mode="paye", has_child_benefit=False, config=config
                )
                # 75k < 100k → no sacrifice
                self.assertEqual(result, 0)

    def test_prompt_salary_sacrifice_explicit_income_target_honoured(self):
        from payday.cli import prompt_salary_sacrifice

        with patch("sys.stdout", new_callable=StringIO):
            config = {
                "salary_sacrifice_enabled": True,
                "monthly_salary_sacrifice": "auto",
                "income_target": 70_000,
                "has_child_benefit": True,
            }
            result = prompt_salary_sacrifice(
                75_000, mode="paye", has_child_benefit=True, config=config
            )
            # Explicit 70k overrides recommended 60k → 5k sacrifice
            self.assertEqual(result, 5_000)

    @patch("payday.cli.PAYECalculator.calculate")
    @patch("sys.stdout", new_callable=StringIO)
    def test_run_once_paye_with_child_benefit_auto(self, mock_stdout, mock_calc):
        from payday.cli import run_once
        from payday.models import SalaryBreakdown

        mock_calc.return_value = SalaryBreakdown(
            mode="PAYE", inputs={}, steps=[], annual_take_home=0, display_take_home=0
        )
        config = {
            "mode": "paye",
            "salary": 75_000,
            "salary_sacrifice_enabled": True,
            "monthly_salary_sacrifice": "auto",
            "income_target": 60_000,
            "has_child_benefit": True,
        }
        with patch("builtins.input", return_value="n"):
            run_once(config)
        mock_calc.assert_called_once()
        _, kwargs = mock_calc.call_args
        self.assertEqual(kwargs.get("salary_sacrifice"), 15_000)
        self.assertTrue(kwargs.get("has_child_benefit"))

    @patch("payday.cli.InsideIR35Calculator.calculate")
    @patch("sys.stdout", new_callable=StringIO)
    def test_run_once_inside_with_child_benefit(self, mock_stdout, mock_calc):
        from payday.cli import run_once
        from payday.models import SalaryBreakdown

        mock_calc.return_value = SalaryBreakdown(
            mode="Inside IR35",
            inputs={},
            steps=[],
            annual_take_home=0,
            display_take_home=0,
        )
        config = {
            "mode": "inside_ir35",
            "day_rate": 500,
            "days_off": 25,
            "working_days": 227,
            "umbrella_margin": 25,
            "is_paystream": False,
            "salary_sacrifice_enabled": True,
            "monthly_salary_sacrifice": "auto",
            "income_target": 60_000,
            "has_child_benefit": True,
        }
        # needs one input for cap prompt? No, income_target explicit → no cap prompt
        # But start_month absent will trigger prompt? Provide start_month to avoid
        config["start_month"] = True
        with patch("builtins.input", return_value="n"):
            run_once(config)
        mock_calc.assert_called_once()
        _, kwargs = mock_calc.call_args
        self.assertTrue(kwargs.get("has_child_benefit"))


if __name__ == "__main__":
    unittest.main()
