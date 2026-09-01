"""Tests for Outside IR35 new features (OutsideIR35 plan).

Covers:
- company_expenses
- director_salary (+ region)
- employment_allowance
- retained_profit
Plus config validation and CLI wiring.
"""

import json
import os
import tempfile
import unittest
from io import StringIO
from unittest.mock import patch

from payday.calculators.outside_ir35 import OutsideIR35Calculator
from payday.constants import PERSONAL_ALLOWANCE, EMPLOYMENT_ALLOWANCE
from payday.config import load_config
from payday.models import StepLine


class _FindMixin:
    def _find(self, bd, label: str) -> StepLine:
        for s in bd.steps:
            if s.label == label:
                return s
        raise AssertionError(f"Step '{label}' not found")

    def _assert_waterfall_reconciles(self, bd) -> None:
        """Assert company subtotals and Take-Home reconcile with the waterfall.

        Company Profit / Distributable are linear running sums from revenue.
        Take-Home is verified as salary - IT - EE NI + net_dividends - loans
        (salary was subtracted to get profit, so a flat cumulative sum would
        be misleading). Informational lines are skipped.

        Raises AssertionError (rather than calling self.assertEquals) so the
        helper type-checks as a plain mixin without a TestCase base.
        """
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
                        f"Take-Home {step.amount} != expected {expected} "
                        f"(salary {salary} - IT {it} - EE {ee} + net_divs {net_divs} - SL {sl} - PGL {pgl})"
                    )
                if step.amount != bd.annual_take_home:
                    raise AssertionError(
                        f"Take-Home {step.amount} != annual_take_home {bd.annual_take_home}"
                    )
                # Don't feed Take-Home into running for subsequent checks (informational)
                continue
            if step.is_subtotal:
                if step.amount != running:
                    raise AssertionError(
                        f"Subtotal '{step.label}' {step.amount} != running sum {running}"
                    )
                running = step.amount
            else:
                running += step.amount


class TestDirectorSalary(_FindMixin, unittest.TestCase):
    def test_default_salary_is_12570(self):
        bd = OutsideIR35Calculator.calculate(500, 240)
        self.assertEqual(self._find(bd, "Director Salary").amount, -PERSONAL_ALLOWANCE)
        self.assertEqual(bd.inputs["salary"], PERSONAL_ALLOWANCE)
        # Default -> no Income Tax / Employee NI lines (preserves old waterfall)
        labels = [s.label for s in bd.steps]
        self.assertNotIn("Income Tax", labels)
        self.assertNotIn("Employee NI", labels)
        self.assertIsNotNone(bd.income_tax)
        self.assertIsNotNone(bd.employee_ni)
        assert bd.income_tax is not None
        assert bd.employee_ni is not None
        self.assertEqual(bd.income_tax.total_tax, 0)
        self.assertEqual(bd.employee_ni.total_ni, 0)

    def test_explicit_default_salary_matches_implicit(self):
        a = OutsideIR35Calculator.calculate(500, 240)
        b = OutsideIR35Calculator.calculate(500, 240, director_salary=12_570)
        self.assertEqual(a.annual_take_home, b.annual_take_home)
        self.assertEqual(
            self._find(a, "Company Profit").amount,
            self._find(b, "Company Profit").amount,
        )

    def test_custom_salary_below_secondary_threshold(self):
        # Salary £5,000 -> no Employer NI, no employee NI/tax, more profit
        bd_default = OutsideIR35Calculator.calculate(500, 240)
        bd_low = OutsideIR35Calculator.calculate(500, 240, director_salary=5_000)
        self.assertEqual(self._find(bd_low, "Director Salary").amount, -5_000)
        self.assertEqual(self._find(bd_low, "Employer NI (15%)").amount, 0)
        # Profit higher because salary + ER NI lower
        self.assertGreater(
            self._find(bd_low, "Company Profit").amount,
            self._find(bd_default, "Company Profit").amount,
        )
        labels = [s.label for s in bd_low.steps]
        self.assertNotIn("Income Tax", labels)
        self.assertNotIn("Employee NI", labels)

    def test_custom_salary_zero(self):
        bd = OutsideIR35Calculator.calculate(500, 240, director_salary=0)
        self.assertEqual(self._find(bd, "Director Salary").amount, 0)
        self.assertEqual(self._find(bd, "Employer NI (15%)").amount, 0)

    def test_custom_salary_above_pa_shows_income_tax_and_employee_ni(self):
        # £50k salary -> IT + EE NI appear on waterfall
        bd = OutsideIR35Calculator.calculate(500, 240, director_salary=50_000)
        self.assertEqual(self._find(bd, "Director Salary").amount, -50_000)
        it = self._find(bd, "Income Tax")
        ni = self._find(bd, "Employee NI")
        self.assertLess(it.amount, 0)  # negative line
        self.assertLess(ni.amount, 0)
        assert bd.income_tax is not None
        assert bd.employee_ni is not None
        self.assertGreater(bd.income_tax.total_tax, 0)
        self.assertGreater(bd.employee_ni.total_ni, 0)
        # Take-home = salary - IT - EE NI + net dividends - SL
        # Should be computed (not salary + net divs)
        self.assertGreater(bd.annual_take_home, 0)
        # Inputs store salary + net_dividends
        self.assertEqual(bd.inputs["salary"], 50_000)
        self.assertIn("net_dividends", bd.inputs)

    def test_custom_salary_scotland_differs_from_ruk(self):
        ruk = OutsideIR35Calculator.calculate(
            500, 240, director_salary=50_000, region="rest_of_uk"
        )
        scot = OutsideIR35Calculator.calculate(
            500, 240, director_salary=50_000, region="scotland"
        )
        assert ruk.income_tax is not None
        assert scot.income_tax is not None
        # Scottish rates differ at 50k (42% vs 40% on higher slice above 43,662)
        self.assertNotEqual(ruk.income_tax.total_tax, scot.income_tax.total_tax)
        # Title inputs region stored
        self.assertEqual(scot.inputs.get("region"), "scotland")
        self.assertNotIn("region", ruk.inputs)

    def test_negative_salary_raises(self):
        with self.assertRaisesRegex(ValueError, "director_salary"):
            OutsideIR35Calculator.calculate(500, 240, director_salary=-1)

    def test_salary_above_revenue_produces_loss(self):
        # Very low revenue but high salary -> loss, clamped dividends 0
        bd = OutsideIR35Calculator.calculate(50, 10, director_salary=50_000)
        # Profit negative, CT 0, dividends 0
        assert bd.corporation_tax is not None
        self.assertEqual(bd.corporation_tax.total_ct, 0)
        assert bd.dividend_tax is not None
        self.assertEqual(bd.dividend_tax.total_tax, 0)


class TestCompanyExpenses(_FindMixin, unittest.TestCase):
    def test_expenses_reduce_profit_and_shown_in_waterfall(self):
        no_exp = OutsideIR35Calculator.calculate(500, 240)
        with_exp = OutsideIR35Calculator.calculate(500, 240, company_expenses=5_000)
        self.assertEqual(self._find(with_exp, "Company Expenses").amount, -5_000)
        self.assertEqual(
            self._find(with_exp, "Company Profit").amount,
            self._find(no_exp, "Company Profit").amount - 5_000,
        )
        assert with_exp.corporation_tax is not None
        assert no_exp.corporation_tax is not None
        self.assertLess(
            with_exp.corporation_tax.total_ct, no_exp.corporation_tax.total_ct
        )
        self.assertIn("company_expenses", with_exp.inputs)
        self.assertNotIn("company_expenses", no_exp.inputs)

    def test_zero_expenses_no_line(self):
        bd = OutsideIR35Calculator.calculate(500, 240, company_expenses=0)
        labels = [s.label for s in bd.steps]
        self.assertNotIn("Company Expenses", labels)

    def test_negative_expenses_raises(self):
        with self.assertRaisesRegex(ValueError, "company_expenses"):
            OutsideIR35Calculator.calculate(500, 240, company_expenses=-1)


class TestEmploymentAllowance(_FindMixin, unittest.TestCase):
    def test_default_no_allowance(self):
        bd = OutsideIR35Calculator.calculate(500, 240)
        labels = [s.label for s in bd.steps]
        self.assertNotIn("Employment Allowance", labels)
        self.assertNotIn("employment_allowance", bd.inputs)
        # ER NI should be the full £1,136 on £12,570 salary
        self.assertEqual(self._find(bd, "Employer NI (15%)").amount, -1136)

    def test_allowance_zeros_er_ni_at_default_salary(self):
        # £12,570 salary -> ER NI £1,136 < £10,500 -> fully offset
        # Display shows gross ER NI plus EA credit so waterfall reconciles.
        bd = OutsideIR35Calculator.calculate(500, 240, employment_allowance=True)
        self.assertEqual(self._find(bd, "Employer NI (15%)").amount, -1136)
        self.assertEqual(self._find(bd, "Employment Allowance").amount, 1136)
        self.assertTrue(bd.inputs["employment_allowance"])
        self.assertEqual(bd.inputs["employment_allowance_used"], 1136)
        # Profit higher by the EA saving
        no_ea = OutsideIR35Calculator.calculate(500, 240, employment_allowance=False)
        self.assertGreater(
            self._find(bd, "Company Profit").amount,
            self._find(no_ea, "Company Profit").amount,
        )

    def test_allowance_partially_offsets_large_salary(self):
        # £80k salary -> ER NI (80k-5k)*15% = 11,250 > EA 10,500 -> leaves £750 net
        # Display shows gross ER NI so waterfall reconciles; net visible via gross+EA.
        bd = OutsideIR35Calculator.calculate(
            500, 240, director_salary=80_000, employment_allowance=True
        )
        self.assertEqual(self._find(bd, "Employer NI (15%)").amount, -11_250)
        self.assertEqual(self._find(bd, "Employment Allowance").amount, 10_500)
        # Without EA, ER NI would be -11,250
        no_ea = OutsideIR35Calculator.calculate(
            500, 240, director_salary=80_000, employment_allowance=False
        )
        self.assertEqual(self._find(no_ea, "Employer NI (15%)").amount, -11_250)

    def test_allowance_no_effect_when_salary_below_secondary_threshold(self):
        bd = OutsideIR35Calculator.calculate(
            500, 240, director_salary=4_000, employment_allowance=True
        )
        self.assertEqual(self._find(bd, "Employer NI (15%)").amount, 0)
        labels = [s.label for s in bd.steps]
        # EA line only when actually used
        self.assertNotIn("Employment Allowance", labels)
        self.assertTrue(bd.inputs["employment_allowance"])

    def test_allowance_constant_is_10500(self):
        self.assertEqual(EMPLOYMENT_ALLOWANCE, 10_500)


class TestRetainedProfit(_FindMixin, unittest.TestCase):
    def test_retained_reduces_dividends_and_div_tax(self):
        no_ret = OutsideIR35Calculator.calculate(500, 240)
        with_ret = OutsideIR35Calculator.calculate(500, 240, retained_profit=20_000)
        self.assertEqual(self._find(with_ret, "Retained in Company").amount, -20_000)
        # Distributable same, dividends lower
        self.assertEqual(
            self._find(with_ret, "Distributable Profit").amount,
            self._find(no_ret, "Distributable Profit").amount,
        )
        assert with_ret.dividend_tax is not None
        assert no_ret.dividend_tax is not None
        self.assertLess(with_ret.dividend_tax.total_tax, no_ret.dividend_tax.total_tax)
        self.assertIn("retained_profit", with_ret.inputs)
        self.assertNotIn("retained_profit", no_ret.inputs)
        # Take-home lower by roughly retained minus div-tax saving
        self.assertLess(with_ret.annual_take_home, no_ret.annual_take_home)

    def test_retained_clamped_to_distributable(self):
        bd = OutsideIR35Calculator.calculate(500, 240)
        dist = int(self._find(bd, "Distributable Profit").amount)
        # Retain far more than distributable -> clamps, dividends 0
        huge = OutsideIR35Calculator.calculate(500, 240, retained_profit=dist + 100_000)
        self.assertEqual(self._find(huge, "Retained in Company").amount, -dist)
        assert huge.dividend_tax is not None
        self.assertEqual(huge.dividend_tax.total_tax, 0)
        self.assertEqual(huge.inputs["net_dividends"], 0)

    def test_retained_does_not_affect_ct(self):
        no_ret = OutsideIR35Calculator.calculate(500, 240)
        with_ret = OutsideIR35Calculator.calculate(500, 240, retained_profit=20_000)
        assert no_ret.corporation_tax is not None
        assert with_ret.corporation_tax is not None
        self.assertEqual(
            no_ret.corporation_tax.total_ct, with_ret.corporation_tax.total_ct
        )
        self.assertEqual(
            self._find(no_ret, "Company Profit").amount,
            self._find(with_ret, "Company Profit").amount,
        )

    def test_zero_retained_no_line(self):
        bd = OutsideIR35Calculator.calculate(500, 240, retained_profit=0)
        labels = [s.label for s in bd.steps]
        self.assertNotIn("Retained in Company", labels)

    def test_negative_retained_raises(self):
        with self.assertRaisesRegex(ValueError, "retained_profit"):
            OutsideIR35Calculator.calculate(500, 240, retained_profit=-1)

    def test_retained_with_expenses_and_pension(self):
        # Combined: expenses 5k + pension 10k + retained 20k
        bd = OutsideIR35Calculator.calculate(
            500,
            240,
            company_expenses=5_000,
            director_pension=10_000,
            retained_profit=20_000,
        )
        self.assertEqual(self._find(bd, "Company Expenses").amount, -5_000)
        self.assertEqual(self._find(bd, "Director Pension").amount, -10_000)
        self.assertEqual(self._find(bd, "Retained in Company").amount, -20_000)


class TestIntegration(_FindMixin, unittest.TestCase):
    def test_all_features_combined(self):
        bd = OutsideIR35Calculator.calculate(
            600,
            240,
            director_salary=9_100,
            company_expenses=3_000,
            director_pension=10_000,
            retained_profit=15_000,
            employment_allowance=True,
            region="scotland",
        )
        # 9,100 salary -> ER NI (9100-5000)*15% = 615 < EA -> fully offset
        # Gross still shown so waterfall reconciles.
        self.assertEqual(self._find(bd, "Employer NI (15%)").amount, -615)
        self.assertEqual(self._find(bd, "Employment Allowance").amount, 615)
        self.assertEqual(self._find(bd, "Company Expenses").amount, -3_000)
        self.assertEqual(self._find(bd, "Director Pension").amount, -10_000)
        self.assertEqual(self._find(bd, "Retained in Company").amount, -15_000)
        self.assertIn("region", bd.inputs)
        self.assertGreater(bd.annual_take_home, 0)


class TestWaterfallReconciliation(_FindMixin, unittest.TestCase):
    def test_default_waterfall_reconciles(self):
        bd = OutsideIR35Calculator.calculate(500, 240)
        self._assert_waterfall_reconciles(bd)

    def test_ea_fully_offset_reconciles(self):
        bd = OutsideIR35Calculator.calculate(500, 240, employment_allowance=True)
        self._assert_waterfall_reconciles(bd)

    def test_ea_partial_reconciles(self):
        bd = OutsideIR35Calculator.calculate(
            500, 240, director_salary=80_000, employment_allowance=True
        )
        self._assert_waterfall_reconciles(bd)

    def test_ea_below_threshold_reconciles(self):
        bd = OutsideIR35Calculator.calculate(
            500, 240, director_salary=4_000, employment_allowance=True
        )
        self._assert_waterfall_reconciles(bd)

    def test_retained_reconciles(self):
        bd = OutsideIR35Calculator.calculate(500, 240, retained_profit=20_000)
        self._assert_waterfall_reconciles(bd)

    def test_expenses_and_retained_reconciles(self):
        bd = OutsideIR35Calculator.calculate(
            500,
            240,
            company_expenses=5_000,
            director_pension=10_000,
            retained_profit=20_000,
        )
        self._assert_waterfall_reconciles(bd)

    def test_all_features_reconciles(self):
        bd = OutsideIR35Calculator.calculate(
            600,
            240,
            director_salary=9_100,
            company_expenses=3_000,
            director_pension=10_000,
            retained_profit=15_000,
            employment_allowance=True,
            region="scotland",
        )
        self._assert_waterfall_reconciles(bd)

    def test_scotland_large_salary_reconciles(self):
        bd = OutsideIR35Calculator.calculate(
            500,
            240,
            director_salary=50_000,
            region="scotland",
            employment_allowance=True,
        )
        self._assert_waterfall_reconciles(bd)


# ── Config validation tests ────────────────────────────────────────────


class TestNewConfigFields(unittest.TestCase):
    def _write(self, data):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(data, f)
        f.close()
        return f.name

    def test_director_salary_accepted(self):
        for val in (12_570, 0, True, None):
            path = self._write({"mode": "outside_ir35", "director_salary": val})
            try:
                res = load_config(path)
                assert res is not None
                self.assertEqual(res["director_salary"], val)
            finally:
                os.unlink(path)

    def test_director_salary_negative_rejected(self):
        path = self._write({"mode": "outside_ir35", "director_salary": -1})
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_director_salary_false_rejected(self):
        path = self._write({"mode": "outside_ir35", "director_salary": False})
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_company_expenses_accepted(self):
        for val in (5_000, 0, True, None):
            path = self._write({"mode": "outside_ir35", "company_expenses": val})
            try:
                res = load_config(path)
                assert res is not None
                self.assertEqual(res["company_expenses"], val)
            finally:
                os.unlink(path)

    def test_company_expenses_negative_rejected(self):
        path = self._write({"mode": "outside_ir35", "company_expenses": -1})
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_retained_profit_accepted(self):
        for val in (10_000, 0, True, None):
            path = self._write({"mode": "outside_ir35", "retained_profit": val})
            try:
                res = load_config(path)
                assert res is not None
                self.assertEqual(res["retained_profit"], val)
            finally:
                os.unlink(path)

    def test_retained_profit_negative_rejected(self):
        path = self._write({"mode": "outside_ir35", "retained_profit": -100})
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_employment_allowance_accepted(self):
        for val in (True, False, None):
            path = self._write({"mode": "outside_ir35", "employment_allowance": val})
            try:
                res = load_config(path)
                assert res is not None
                self.assertIs(res["employment_allowance"], val)
            finally:
                os.unlink(path)

    def test_employment_allowance_wrong_type_rejected(self):
        for bad in ("yes", 1, 0, "true"):
            path = self._write({"mode": "outside_ir35", "employment_allowance": bad})
            try:
                with self.assertRaises(ValueError):
                    load_config(path)
            finally:
                os.unlink(path)


# ── CLI wiring tests ────────────────────────────────────────────────────


class TestOutsideIR35CLI(unittest.TestCase):
    def test_prompt_employment_allowance_config_true(self):
        from payday.cli import prompt_employment_allowance

        with patch("sys.stdout", new_callable=StringIO):
            self.assertTrue(prompt_employment_allowance({"employment_allowance": True}))

    def test_prompt_employment_allowance_config_false(self):
        from payday.cli import prompt_employment_allowance

        with patch("sys.stdout", new_callable=StringIO):
            self.assertFalse(
                prompt_employment_allowance({"employment_allowance": False})
            )

    def test_prompt_employment_allowance_interactive_yes(self):
        from payday.cli import prompt_employment_allowance

        with patch("builtins.input", return_value="y"):
            self.assertTrue(prompt_employment_allowance())

    def test_prompt_employment_allowance_interactive_no(self):
        from payday.cli import prompt_employment_allowance

        with patch("builtins.input", return_value="n"):
            self.assertFalse(prompt_employment_allowance())

    @patch("payday.cli.OutsideIR35Calculator.calculate")
    @patch("builtins.input", side_effect=["n"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_full_config_with_all_new_fields(self, mock_stdout, mock_input, mock_calc):
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
            "director_salary": 9_100,
            "company_expenses": 3_000,
            "director_pension": 5_000,
            "retained_profit": 10_000,
            "employment_allowance": True,
            "region": "scotland",
        }
        run_once(config)
        mock_calc.assert_called_once()
        _, kwargs = mock_calc.call_args
        self.assertEqual(kwargs["director_salary"], 9_100)
        self.assertEqual(kwargs["company_expenses"], 3_000)
        self.assertEqual(kwargs["retained_profit"], 10_000)
        self.assertTrue(kwargs["employment_allowance"])
        self.assertEqual(kwargs["region"], "scotland")

    @patch("payday.cli.OutsideIR35Calculator.calculate")
    @patch(
        "builtins.input",
        side_effect=[
            "3",  # mode
            "600",  # day rate
            "",  # start month (full year)
            "",  # other income (default 0)
            "",  # days off (default 25)
            "",  # accept working days
            "y",  # Scotland? y
            "9100",  # director salary
            "3000",  # company expenses
            "5000",  # director pension
            "10000",  # retained
            "y",  # employment allowance
            "n",  # child benefit? [y/N]
            "plan1",  # student loan plan
            "n",  # postgraduate
        ],
    )
    @patch("sys.stdout", new_callable=StringIO)
    def test_interactive_prompts_all_new_fields(
        self, mock_stdout, mock_input, mock_calc
    ):
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
        self.assertEqual(kwargs["director_salary"], 9100)
        self.assertEqual(kwargs["company_expenses"], 3000)
        self.assertEqual(kwargs["director_pension"], 5000)
        self.assertEqual(kwargs["retained_profit"], 10000)
        self.assertTrue(kwargs["employment_allowance"])
        self.assertEqual(kwargs["region"], "scotland")


if __name__ == "__main__":
    unittest.main()
