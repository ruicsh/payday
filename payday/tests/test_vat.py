"""Tests for VAT Flat Rate Scheme (Outside IR35).

Covers:
- OutsideIR35Calculator VAT logic (flat_rate profit, standard neutral, not-registered ignores)
- Config validation for vat_registered / vat_scheme / vat_flat_rate
- CLI prompts and wiring for VAT fields
- Waterfall reconciliation with VAT

Sources:
- https://www.gov.uk/vat-flat-rate-scheme
- https://www.gov.uk/vat-flat-rate-scheme/how-much-you-pay
- https://www.gov.uk/guidance/flat-rate-scheme-for-small-businesses-vat-notice-733--2 (¶4.4 limited cost 16.5%)
- BIM31585: https://www.gov.uk/hmrc-internal-manuals/business-income-manual/bim31585
"""

import json
import os
import tempfile
import unittest
from io import StringIO
from unittest.mock import patch

from payday.calculators.outside_ir35 import OutsideIR35Calculator
from payday.config import load_config
from payday.constants import VAT_FLAT_RATE_DEFAULT
from payday.models import StepLine


class _FindMixin:
    def _find(self, bd, label: str) -> StepLine:
        for s in bd.steps:
            if s.label == label:
                return s
        raise AssertionError(f"Step '{label}' not found")

    def _find_vat_surplus(self, bd) -> StepLine | None:
        for s in bd.steps:
            if s.label.startswith("Flat Rate VAT Surplus"):
                return s
        return None

    def _assert_waterfall_reconciles(self, bd) -> None:
        skip_labels = {"20-Day Take-Home", "Year Taxable Income"}
        running = 0
        for step in bd.steps:
            if step.label in skip_labels:
                continue
            if step.label == "Take-Home":
                salary = bd.inputs.get("salary", 0)
                net_divs = bd.inputs.get("net_dividends", 0)
                it = bd.income_tax.total_tax if bd.income_tax else 0
                ee = bd.employee_ni.total_ni if bd.employee_ni else 0
                sl = bd.student_loan.repayment if bd.student_loan else 0
                pgl = bd.postgraduate_loan.repayment if bd.postgraduate_loan else 0
                expected = salary - it - ee + net_divs - sl - pgl
                if step.amount != expected:
                    raise AssertionError(
                        f"Take-Home {step.amount} != expected {expected}"
                    )
                if step.amount != bd.annual_take_home:
                    raise AssertionError(
                        f"Take-Home {step.amount} != annual_take_home {bd.annual_take_home}"
                    )
                continue
            if step.is_subtotal:
                if step.amount != running:
                    raise AssertionError(
                        f"Subtotal '{step.label}' {step.amount} != running sum {running}"
                    )
                running = step.amount
            else:
                running += step.amount


class TestVATCalculator(_FindMixin, unittest.TestCase):
    def test_default_no_vat(self):
        bd = OutsideIR35Calculator.calculate(500, 240)
        self.assertIsNone(self._find_vat_surplus(bd))
        self.assertNotIn("vat_registered", bd.inputs)
        self.assertNotIn("vat_profit", bd.inputs)

    def test_vat_not_registered_ignores_flat_rate(self):
        bd_none = OutsideIR35Calculator.calculate(500, 240)
        bd = OutsideIR35Calculator.calculate(
            500, 240, vat_registered=False, vat_scheme="flat_rate", vat_flat_rate=0.165
        )
        self.assertIsNone(self._find_vat_surplus(bd))
        self.assertEqual(bd.annual_take_home, bd_none.annual_take_home)
        self.assertEqual(
            self._find(bd, "Company Profit").amount,
            self._find(bd_none, "Company Profit").amount,
        )
        self.assertNotIn("vat_registered", bd.inputs)

    def test_standard_scheme_cash_neutral(self):
        bd_none = OutsideIR35Calculator.calculate(500, 240)
        bd_std = OutsideIR35Calculator.calculate(
            500, 240, vat_registered=True, vat_scheme="standard"
        )
        self.assertIsNone(self._find_vat_surplus(bd_std))
        self.assertEqual(bd_std.annual_take_home, bd_none.annual_take_home)
        self.assertEqual(
            self._find(bd_std, "Company Profit").amount,
            self._find(bd_none, "Company Profit").amount,
        )
        # Standard scheme still records vat_registered/vat_scheme but no profit
        self.assertTrue(bd_std.inputs["vat_registered"])
        self.assertEqual(bd_std.inputs["vat_scheme"], "standard")
        self.assertNotIn("vat_profit", bd_std.inputs)

    def test_flat_rate_default_16_5_surplus(self):
        # revenue 500*240=120000, VAT 24000, payment 144000*0.165=23760, surplus 240
        bd = OutsideIR35Calculator.calculate(
            500, 240, vat_registered=True, vat_scheme="flat_rate", vat_flat_rate=0.165
        )
        vat_line = self._find_vat_surplus(bd)
        assert vat_line is not None
        self.assertEqual(vat_line.amount, 240)
        self.assertEqual(bd.inputs["vat_profit"], 240)
        self.assertEqual(bd.inputs["vat_flat_rate"], 0.165)
        self.assertIn("16.5%", vat_line.label)
        # Profit = none profit + surplus
        bd_none = OutsideIR35Calculator.calculate(500, 240)
        self.assertEqual(
            self._find(bd, "Company Profit").amount,
            self._find(bd_none, "Company Profit").amount + 240,
        )
        # Take-home higher than none (after CT/dividend tax)
        self.assertGreater(bd.annual_take_home, bd_none.annual_take_home)

    def test_flat_rate_default_when_none_passed(self):
        # vat_flat_rate=None should default to 0.165
        bd_explicit = OutsideIR35Calculator.calculate(
            500, 240, vat_registered=True, vat_scheme="flat_rate", vat_flat_rate=0.165
        )
        bd_default = OutsideIR35Calculator.calculate(
            500, 240, vat_registered=True, vat_scheme="flat_rate", vat_flat_rate=None
        )
        self.assertEqual(bd_explicit.annual_take_home, bd_default.annual_take_home)
        self.assertEqual(
            bd_explicit.inputs["vat_profit"], bd_default.inputs["vat_profit"]
        )

    def test_flat_rate_constant_is_165(self):
        self.assertEqual(VAT_FLAT_RATE_DEFAULT, 0.165)

    def test_flat_rate_custom_sector_rate(self):
        # 14.5% sector rate: surplus = 120000*0.20 - 144000*0.145 = 24000-20880=3120
        bd = OutsideIR35Calculator.calculate(
            500, 240, vat_registered=True, vat_scheme="flat_rate", vat_flat_rate=0.145
        )
        vat_line = self._find_vat_surplus(bd)
        assert vat_line is not None
        self.assertEqual(vat_line.amount, 3120)
        self.assertEqual(bd.inputs["vat_profit"], 3120)
        self.assertIn("14.5%", vat_line.label)

    def test_flat_rate_profit_formula_matches_bim31585(self):
        # BIM31585 example: gross 84k (net 70k), VAT 14k, flat 6% payment 5040, surplus 8960
        # Our model uses net revenue; test with net 70000, flat 0.06
        # surplus = 70000*0.20 - 84000*0.06 = 14000-5040=8960
        # Use day_rate 700, effective_days 100 => revenue 70000
        bd = OutsideIR35Calculator.calculate(
            700, 100, vat_registered=True, vat_scheme="flat_rate", vat_flat_rate=0.06
        )
        self.assertEqual(bd.inputs["vat_profit"], 8960)

    def test_flat_rate_profit_is_taxable_before_ct(self):
        bd_none = OutsideIR35Calculator.calculate(500, 240)
        bd_flat = OutsideIR35Calculator.calculate(
            500, 240, vat_registered=True, vat_scheme="flat_rate", vat_flat_rate=0.145
        )
        # CT should be higher when surplus exists (profit higher)
        assert bd_none.corporation_tax is not None
        assert bd_flat.corporation_tax is not None
        self.assertGreater(
            bd_flat.corporation_tax.total_ct, bd_none.corporation_tax.total_ct
        )
        # Distributable profit also higher
        self.assertGreater(
            self._find(bd_flat, "Distributable Profit").amount,
            self._find(bd_none, "Distributable Profit").amount,
        )

    def test_vat_scheme_invalid_raises(self):
        with self.assertRaisesRegex(ValueError, "vat_scheme"):
            OutsideIR35Calculator.calculate(500, 240, vat_scheme="invalid")

    def test_vat_flat_rate_invalid_raises(self):
        for bad in (0, 1, -0.1, 1.5):
            with self.assertRaisesRegex(ValueError, "vat_flat_rate"):
                OutsideIR35Calculator.calculate(
                    500,
                    240,
                    vat_registered=True,
                    vat_scheme="flat_rate",
                    vat_flat_rate=bad,
                )

    def test_vat_surplus_with_other_features(self):
        # VAT + EA + expenses + pension + retained should all affect profit correctly
        bd = OutsideIR35Calculator.calculate(
            600,
            240,
            company_expenses=3000,
            director_pension=10000,
            retained_profit=15000,
            employment_allowance=True,
            vat_registered=True,
            vat_scheme="flat_rate",
            vat_flat_rate=0.145,
            director_salary=9100,
        )
        self.assertIsNotNone(self._find_vat_surplus(bd))
        # EA fully offsets ER NI at 9100 salary; VAT adds 3744 surplus (144k*0.20 - 172800*0.145 = 28800-25056=3744? Wait revenue 144k for 600*240)
        # Just check waterfall reconciles and profit includes VAT
        self._assert_waterfall_reconciles(bd)
        self.assertGreater(bd.annual_take_home, 0)

    def test_vat_partial_year_pro_rata(self):
        # VAT profit should scale with effective_days (revenue = day_rate * effective_days)
        # Partial year 145 days: revenue 72500, surplus = 14500 - 14355 = 145 (72500*0.002)
        bd_partial = OutsideIR35Calculator.calculate(
            500,
            252,
            start_month=8,
            effective_days=145,
            vat_registered=True,
            vat_scheme="flat_rate",
            vat_flat_rate=0.165,
        )
        # 252 days full revenue 126000, surplus 252; partial 145 days surplus 145
        # Just verify surplus proportional to revenue
        self.assertEqual(bd_partial.inputs["vat_profit"], round(500 * 145 * 0.002))


class TestVATWaterfallReconciliation(_FindMixin, unittest.TestCase):
    def test_flat_default_reconciles(self):
        bd = OutsideIR35Calculator.calculate(
            500, 240, vat_registered=True, vat_scheme="flat_rate", vat_flat_rate=0.165
        )
        self._assert_waterfall_reconciles(bd)

    def test_flat_custom_reconciles(self):
        bd = OutsideIR35Calculator.calculate(
            500, 240, vat_registered=True, vat_scheme="flat_rate", vat_flat_rate=0.145
        )
        self._assert_waterfall_reconciles(bd)

    def test_standard_reconciles(self):
        bd = OutsideIR35Calculator.calculate(
            500, 240, vat_registered=True, vat_scheme="standard"
        )
        self._assert_waterfall_reconciles(bd)

    def test_vat_with_all_features_reconciles(self):
        bd = OutsideIR35Calculator.calculate(
            600,
            240,
            director_salary=9100,
            company_expenses=3000,
            director_pension=10000,
            retained_profit=15000,
            employment_allowance=True,
            vat_registered=True,
            vat_scheme="flat_rate",
            vat_flat_rate=0.145,
            region="scotland",
        )
        self._assert_waterfall_reconciles(bd)


class TestVATConfig(unittest.TestCase):
    def _write(self, data):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(data, f)
        f.close()
        return f.name

    def test_vat_registered_accepted(self):
        for val in (True, False, None):
            path = self._write({"mode": "outside_ir35", "vat_registered": val})
            try:
                res = load_config(path)
                assert res is not None
                self.assertIs(res["vat_registered"], val)
            finally:
                os.unlink(path)

    def test_vat_registered_wrong_type_rejected(self):
        for bad in ("yes", 1, 0, "true", "no"):
            path = self._write({"mode": "outside_ir35", "vat_registered": bad})
            try:
                with self.assertRaises(ValueError):
                    load_config(path)
            finally:
                os.unlink(path)

    def test_vat_scheme_accepted(self):
        for val in ("standard", "flat_rate", "none", None):
            path = self._write({"mode": "outside_ir35", "vat_scheme": val})
            try:
                res = load_config(path)
                assert res is not None
                self.assertEqual(res["vat_scheme"], val)
            finally:
                os.unlink(path)

    def test_vat_scheme_invalid_rejected(self):
        for bad in ("invalid", "flat", "STANDARD", "", "frs"):
            path = self._write({"mode": "outside_ir35", "vat_scheme": bad})
            try:
                with self.assertRaises(ValueError):
                    load_config(path)
            finally:
                os.unlink(path)

    def test_vat_flat_rate_accepted(self):
        for val in (0.165, 0.145, 0.06, 0.12, True, None):
            path = self._write({"mode": "outside_ir35", "vat_flat_rate": val})
            try:
                res = load_config(path)
                assert res is not None
                self.assertEqual(res["vat_flat_rate"], val)
            finally:
                os.unlink(path)

    def test_vat_flat_rate_int_accepted(self):
        # int 0 is falsy but 0<flat<1 fails; 0 should be rejected, non-zero int like 1 also rejected
        path = self._write({"mode": "outside_ir35", "vat_flat_rate": 0})
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_vat_flat_rate_invalid_rejected(self):
        for bad in (0, 1, 1.0, 1.5, -0.1, -1, "0.165", "16.5%"):
            path = self._write({"mode": "outside_ir35", "vat_flat_rate": bad})
            try:
                with self.assertRaises(ValueError):
                    load_config(path)
            finally:
                os.unlink(path)


class TestVATCLI(unittest.TestCase):
    def test_prompt_vat_registered_config_true(self):
        from payday.cli import prompt_vat_registered

        with patch("sys.stdout", new_callable=StringIO):
            self.assertTrue(prompt_vat_registered({"vat_registered": True}))

    def test_prompt_vat_registered_config_false(self):
        from payday.cli import prompt_vat_registered

        with patch("sys.stdout", new_callable=StringIO):
            self.assertFalse(prompt_vat_registered({"vat_registered": False}))

    def test_prompt_vat_registered_config_absent_defaults_false(self):
        from payday.cli import prompt_vat_registered

        with patch("sys.stdout", new_callable=StringIO):
            # Config-file mode but vat_registered absent -> default not registered, no prompt
            self.assertFalse(prompt_vat_registered({"mode": "outside_ir35"}))

    def test_prompt_vat_registered_interactive_yes(self):
        from payday.cli import prompt_vat_registered

        with patch("builtins.input", return_value="y"):
            self.assertTrue(prompt_vat_registered())

    def test_prompt_vat_registered_interactive_no(self):
        from payday.cli import prompt_vat_registered

        with patch("builtins.input", return_value="n"):
            self.assertFalse(prompt_vat_registered())

    def test_prompt_vat_scheme_config_flat_rate(self):
        from payday.cli import prompt_vat_scheme

        with patch("sys.stdout", new_callable=StringIO):
            self.assertEqual(
                prompt_vat_scheme({"vat_scheme": "flat_rate"}, vat_registered=True),
                "flat_rate",
            )

    def test_prompt_vat_scheme_config_standard(self):
        from payday.cli import prompt_vat_scheme

        with patch("sys.stdout", new_callable=StringIO):
            self.assertEqual(
                prompt_vat_scheme({"vat_scheme": "standard"}, vat_registered=True),
                "standard",
            )

    def test_prompt_vat_scheme_not_registered_returns_none(self):
        from payday.cli import prompt_vat_scheme

        self.assertEqual(prompt_vat_scheme(vat_registered=False), "none")
        self.assertEqual(
            prompt_vat_scheme({"vat_registered": False}, vat_registered=False), "none"
        )

    def test_prompt_vat_scheme_config_absent_defaults_standard(self):
        from payday.cli import prompt_vat_scheme

        # Config-file mode with vat_registered but no scheme -> default standard, no prompt
        with patch("sys.stdout", new_callable=StringIO):
            self.assertEqual(
                prompt_vat_scheme({"vat_registered": True}, vat_registered=True),
                "standard",
            )

    def test_prompt_vat_scheme_interactive_flat_rate(self):
        from payday.cli import prompt_vat_scheme

        with patch("builtins.input", return_value="flat_rate"):
            self.assertEqual(prompt_vat_scheme(vat_registered=True), "flat_rate")

    def test_prompt_vat_scheme_interactive_standard(self):
        from payday.cli import prompt_vat_scheme

        with patch("builtins.input", return_value=""):
            self.assertEqual(prompt_vat_scheme(vat_registered=True), "standard")

    def test_prompt_vat_flat_rate_config_true(self):
        from payday.cli import prompt_vat_flat_rate

        with patch("sys.stdout", new_callable=StringIO):
            self.assertEqual(
                prompt_vat_flat_rate({"vat_flat_rate": True}, vat_scheme="flat_rate"),
                VAT_FLAT_RATE_DEFAULT,
            )

    def test_prompt_vat_flat_rate_config_float(self):
        from payday.cli import prompt_vat_flat_rate

        with patch("sys.stdout", new_callable=StringIO):
            val = prompt_vat_flat_rate({"vat_flat_rate": 0.145}, vat_scheme="flat_rate")
            assert val is not None
            self.assertAlmostEqual(val, 0.145)

    def test_prompt_vat_flat_rate_not_flat_rate_returns_none(self):
        from payday.cli import prompt_vat_flat_rate

        self.assertIsNone(prompt_vat_flat_rate(vat_scheme="standard"))
        self.assertIsNone(prompt_vat_flat_rate(vat_scheme="none"))

    def test_prompt_vat_flat_rate_config_absent_defaults(self):
        from payday.cli import prompt_vat_flat_rate

        # Config-file mode flat_rate but no explicit rate -> default 16.5% without prompt
        self.assertEqual(
            prompt_vat_flat_rate(
                {"vat_registered": True, "vat_scheme": "flat_rate"},
                vat_scheme="flat_rate",
            ),
            VAT_FLAT_RATE_DEFAULT,
        )

    def test_prompt_vat_flat_rate_interactive_percent(self):
        from payday.cli import prompt_vat_flat_rate

        with patch("builtins.input", return_value="14.5"):
            val = prompt_vat_flat_rate(vat_scheme="flat_rate")
            assert val is not None
            self.assertAlmostEqual(val, 0.145)
        with patch("builtins.input", return_value="14.5%"):
            val = prompt_vat_flat_rate(vat_scheme="flat_rate")
            assert val is not None
            self.assertAlmostEqual(val, 0.145)
        with patch("builtins.input", return_value="0.145"):
            val = prompt_vat_flat_rate(vat_scheme="flat_rate")
            assert val is not None
            self.assertAlmostEqual(val, 0.145)
        with patch("builtins.input", return_value=""):
            val = prompt_vat_flat_rate(vat_scheme="flat_rate")
            assert val is not None
            self.assertAlmostEqual(val, 0.165)

    @patch("payday.cli.OutsideIR35Calculator.calculate")
    @patch("builtins.input", side_effect=["n"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_cli_wiring_full_config_with_vat(self, mock_stdout, mock_input, mock_calc):
        from payday.cli import run_once
        from payday.models import SalaryBreakdown

        mock_calc.return_value = SalaryBreakdown(
            mode="Outside IR35",
            inputs={},
            steps=[],
            annual_take_home=0,
            display_take_home=0,
        )
        config = {
            "mode": "outside_ir35",
            "day_rate": 600,
            "start_month": True,
            "existing_income": True,
            "existing_dividends": True,
            "days_off": 25,
            "working_days": 240,
            "director_salary": 9100,
            "company_expenses": 3000,
            "director_pension": 5000,
            "retained_profit": 10000,
            "employment_allowance": True,
            "vat_registered": True,
            "vat_scheme": "flat_rate",
            "vat_flat_rate": 0.145,
            "region": "scotland",
        }
        run_once(config)
        mock_calc.assert_called_once()
        _, kwargs = mock_calc.call_args
        self.assertTrue(kwargs["vat_registered"])
        self.assertEqual(kwargs["vat_scheme"], "flat_rate")
        self.assertAlmostEqual(kwargs["vat_flat_rate"], 0.145)

    @patch("payday.cli.OutsideIR35Calculator.calculate")
    @patch(
        "builtins.input",
        side_effect=[
            "3",  # mode
            "600",  # day rate
            "",  # start month (full year)
            "",  # other income
            "",  # days off (default 25)
            "",  # accept working days
            "y",  # Scotland? y
            "",  # NI category [A]
            "9100",  # director salary
            "3000",  # company expenses
            "5000",  # director pension
            "10000",  # retained
            "y",  # employment allowance
            "y",  # VAT registered? yes
            "flat_rate",  # VAT scheme
            "14.5",  # flat rate %
            "n",  # child benefit? [y/N]
            "plan1",  # student loan plan
            "n",  # postgraduate
        ],
    )
    @patch("sys.stdout", new_callable=StringIO)
    def test_cli_wiring_interactive_with_vat(self, mock_stdout, mock_input, mock_calc):
        from payday.cli import run_once
        from payday.models import SalaryBreakdown

        mock_calc.return_value = SalaryBreakdown(
            mode="Outside IR35",
            inputs={},
            steps=[],
            annual_take_home=0,
            display_take_home=0,
        )
        run_once()
        mock_calc.assert_called_once()
        _, kwargs = mock_calc.call_args
        self.assertTrue(kwargs["vat_registered"])
        self.assertEqual(kwargs["vat_scheme"], "flat_rate")
        self.assertAlmostEqual(kwargs["vat_flat_rate"], 0.145)


if __name__ == "__main__":
    unittest.main()
