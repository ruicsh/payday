import unittest
from payday.calculators.sole_trader import SoleTraderCalculator
from payday.national_insurance import calc_class4_ni


class TestClass4NI(unittest.TestCase):
    """Class 4 NI — https://www.gov.uk/self-employed-national-insurance-rates"""

    def test_below_lpl_no_ni(self):
        res = calc_class4_ni(10_000)
        self.assertEqual(res.total_ni, 0)
        self.assertEqual(res.main_band, 0)
        self.assertEqual(res.upper_band, 0)

    def test_at_lpl_no_ni(self):
        res = calc_class4_ni(12_570)
        self.assertEqual(res.total_ni, 0)

    def test_main_rate_only(self):
        # £30,000: (30000-12570)*0.06 = 17430*0.06 = 1045.8 -> 1046
        res = calc_class4_ni(30_000)
        self.assertEqual(res.main_band, 17_430)
        self.assertEqual(res.total_ni, 1_046)

    def test_main_rate_50k(self):
        # £50,000: (50000-12570)*0.06 = 37430*0.06 = 2245.8 -> 2246
        res = calc_class4_ni(50_000)
        self.assertEqual(res.total_ni, 2_246)
        self.assertEqual(res.upper_band, 0)

    def test_upper_rate(self):
        # £75,000: 37700*0.06=2262 + (75000-50270)*0.02=24730*0.02=494.6->495 => 2757
        res = calc_class4_ni(75_000)
        self.assertEqual(res.main_band, 37_700)
        self.assertEqual(res.main_ni, 2_262)
        self.assertEqual(res.upper_band, 24_730)
        self.assertEqual(res.upper_ni, 495)
        self.assertEqual(res.total_ni, 2_757)

    def test_exact_upper_limit(self):
        res = calc_class4_ni(50_270)
        self.assertEqual(res.upper_band, 0)
        self.assertEqual(res.total_ni, 2_262)  # 37700*0.06

    def test_zero_profit(self):
        res = calc_class4_ni(0)
        self.assertEqual(res.total_ni, 0)

    def test_with_existing_self_employment(self):
        # existing 20k + profit 30k = total 50k => total NI 2246, existing NI 7430*0.06=446 => incremental 1800
        res = calc_class4_ni(30_000, existing_self_employment=20_000)
        self.assertEqual(res.total_ni, 1_800)
        # existing 10k (below LPL) + profit 40k = total 50k => incremental is full 2246
        res2 = calc_class4_ni(40_000, existing_self_employment=10_000)
        self.assertEqual(res2.total_ni, 2_246)

    def test_existing_covers_all_main_band(self):
        # existing 50270 covers full main band (37700), new profit 10k goes fully to upper rate 2%
        res = calc_class4_ni(10_000, existing_self_employment=50_270)
        self.assertEqual(res.main_band, 0)
        self.assertEqual(res.upper_band, 10_000)
        self.assertEqual(res.total_ni, 200)

    def test_doctest_known_answers(self):
        self.assertEqual(calc_class4_ni(30_000).total_ni, 1_046)
        self.assertEqual(calc_class4_ni(75_000).total_ni, 2_757)
        self.assertEqual(calc_class4_ni(10_000).total_ni, 0)


class TestSoleTraderCalculator(unittest.TestCase):
    def _find_step(self, breakdown, label):
        for step in breakdown.steps:
            if step.label == label:
                return step
        self.fail(f"Step '{label}' not found")

    def test_full_pipeline_500_day(self):
        b = SoleTraderCalculator.calculate(500, 240)
        self.assertEqual(b.mode, "Sole Trader")
        self.assertEqual(b.inputs["day_rate"], 500)
        self.assertEqual(b.inputs["working_days"], 240)
        self.assertEqual(self._find_step(b, "Turnover").amount, 120_000)
        self.assertEqual(self._find_step(b, "Trading Profit").amount, 120_000)
        # Class 4 on 120k: main 37700*0.06=2262 + upper 69730*0.02=1394.6->1395 => 3657
        self.assertEqual(self._find_step(b, "Class 4 NI").amount, -3_657)
        assert b.class4_ni is not None
        self.assertEqual(b.class4_ni.total_ni, 3_657)
        # PA taper: ANI 120k => PA 2570, so IT on 120k is higher
        self.assertGreater(b.annual_take_home, 0)
        self.assertEqual(b.display_take_home, round(b.annual_take_home / 240 * 20))
        self.assertEqual(b.year_taxable_income, 120_000)

    def test_low_profit_no_tax_no_ni(self):
        b = SoleTraderCalculator.calculate(50, 100)  # 5k turnover
        self.assertEqual(self._find_step(b, "Turnover").amount, 5_000)
        self.assertEqual(self._find_step(b, "Trading Profit").amount, 5_000)
        assert b.class4_ni is not None
        self.assertEqual(b.class4_ni.total_ni, 0)
        assert b.income_tax is not None
        self.assertEqual(b.income_tax.total_tax, 0)
        self.assertEqual(b.annual_take_home, 5_000)

    def test_business_expenses_reduce_profit_and_tax(self):
        base = SoleTraderCalculator.calculate(500, 240)
        with_exp = SoleTraderCalculator.calculate(500, 240, business_expenses=10_000)
        self.assertEqual(self._find_step(with_exp, "Business Expenses").amount, -10_000)
        self.assertEqual(self._find_step(with_exp, "Trading Profit").amount, 110_000)
        assert with_exp.class4_ni is not None
        assert base.class4_ni is not None
        self.assertLess(with_exp.class4_ni.total_ni, base.class4_ni.total_ni)
        assert with_exp.income_tax is not None
        assert base.income_tax is not None
        self.assertLess(with_exp.income_tax.total_tax, base.income_tax.total_tax)
        self.assertIn("business_expenses", with_exp.inputs)

    def test_business_expenses_exceeds_turnover_clamps_to_zero(self):
        b = SoleTraderCalculator.calculate(
            100, 100, business_expenses=20_000
        )  # turnover 10k
        self.assertEqual(self._find_step(b, "Trading Profit").amount, 0)
        self.assertEqual(b.annual_take_home, 0)
        assert b.class4_ni is not None
        self.assertEqual(b.class4_ni.total_ni, 0)

    def test_personal_pension_reduces_taxable_profit_not_class4(self):
        base = SoleTraderCalculator.calculate(500, 240)
        with_pension = SoleTraderCalculator.calculate(500, 240, personal_pension=20_000)
        self.assertEqual(
            self._find_step(with_pension, "Personal Pension").amount, -20_000
        )
        self.assertEqual(
            self._find_step(with_pension, "Taxable Profit").amount, 100_000
        )
        # Class 4 is on trading profit (120k) in both cases
        assert with_pension.class4_ni is not None
        assert base.class4_ni is not None
        self.assertEqual(with_pension.class4_ni.total_ni, base.class4_ni.total_ni)
        assert with_pension.income_tax is not None
        assert base.income_tax is not None
        self.assertLess(with_pension.income_tax.total_tax, base.income_tax.total_tax)
        self.assertIn("personal_pension", with_pension.inputs)

    def test_personal_pension_capped_at_60k(self):
        b = SoleTraderCalculator.calculate(500, 240, personal_pension=100_000)
        self.assertEqual(self._find_step(b, "Personal Pension").amount, -60_000)
        self.assertEqual(b.inputs["personal_pension"], 60_000)

    def test_personal_pension_greater_than_profit(self):
        b = SoleTraderCalculator.calculate(
            100, 100, personal_pension=20_000
        )  # turnover 10k
        # trading 10k, pension 20k => taxable 0, IT 0, Class4 0 (10k below LPL)
        self.assertEqual(self._find_step(b, "Taxable Profit").amount, 0)
        assert b.income_tax is not None
        self.assertEqual(b.income_tax.total_tax, 0)
        assert b.class4_ni is not None
        self.assertEqual(b.class4_ni.total_ni, 0)

    def test_existing_self_employment_consumes_bands(self):
        without = SoleTraderCalculator.calculate(500, 240)
        with_se = SoleTraderCalculator.calculate(
            500, 240, existing_self_employment=20_000
        )
        self.assertIn("existing_self_employment", with_se.inputs)
        # Class 4 incremental should be lower when existing covers part of band
        assert with_se.class4_ni is not None
        assert without.class4_ni is not None
        self.assertLess(with_se.class4_ni.total_ni, without.class4_ni.total_ni)
        assert with_se.income_tax is not None
        assert without.income_tax is not None
        self.assertGreater(with_se.income_tax.total_tax, without.income_tax.total_tax)
        self.assertEqual(
            with_se.year_taxable_income,
            with_se.inputs["existing_self_employment"]
            + 120_000
            - (
                with_se.inputs.get("personal_pension", 0)
                if "personal_pension" in with_se.inputs
                else 0
            ),
        )

    def test_existing_income_only_consumes_it(self):
        base = SoleTraderCalculator.calculate(500, 240)
        with_emp = SoleTraderCalculator.calculate(500, 240, existing_income=20_000)
        # Class 4 unchanged (only self-employment consumes it)
        assert with_emp.class4_ni is not None
        assert base.class4_ni is not None
        self.assertEqual(with_emp.class4_ni.total_ni, base.class4_ni.total_ni)
        assert with_emp.income_tax is not None
        assert base.income_tax is not None
        self.assertGreater(with_emp.income_tax.total_tax, base.income_tax.total_tax)

    def test_partial_year_august_start(self):
        b = SoleTraderCalculator.calculate(500, 240, start_month=8)
        self.assertEqual(b.inputs["start_month"], 8)
        self.assertEqual(b.inputs["contract_months"], 8)
        self.assertEqual(b.inputs["effective_working_days"], 160)
        self.assertEqual(b.inputs["contract_period"], "Aug 2026–Apr 2027 (8 months)")
        self.assertEqual(self._find_step(b, "Turnover").amount, 80_000)
        self.assertEqual(b.display_take_home, round(b.annual_take_home / 160 * 20))

    def test_effective_days_overrides_prorated(self):
        b = SoleTraderCalculator.calculate(500, 240, start_month=8, effective_days=170)
        self.assertEqual(b.inputs["effective_working_days"], 170)
        self.assertEqual(self._find_step(b, "Turnover").amount, 85_000)

    def test_zero_working_days_raises(self):
        with self.assertRaisesRegex(ValueError, "working_days must be > 0"):
            SoleTraderCalculator.calculate(500, 0)

    def test_negative_expenses_raises(self):
        with self.assertRaisesRegex(ValueError, "business_expenses"):
            SoleTraderCalculator.calculate(500, 240, business_expenses=-1)

    def test_negative_pension_raises(self):
        with self.assertRaisesRegex(ValueError, "personal_pension"):
            SoleTraderCalculator.calculate(500, 240, personal_pension=-1)

    def test_year_taxable_income_full_year(self):
        b = SoleTraderCalculator.calculate(500, 240)
        # year_taxable is taxable + existing; for this case trading 120k, no pension, no existing => 120k
        self.assertEqual(b.year_taxable_income, 120_000)
        self.assertEqual(self._find_step(b, "Year Taxable Income").amount, 120_000)

    def test_year_taxable_income_with_existing(self):
        b = SoleTraderCalculator.calculate(
            500,
            240,
            start_month=8,
            existing_income=10_000,
            existing_self_employment=5_000,
            business_expenses=10_000,
            personal_pension=5_000,
        )
        # turnover 500*160=80k, trading 70k, taxable 65k, +15k existing =80k? Wait existing is income+SE
        # Actually calculation: trading 70k, pension 5k => taxable 65k, year_taxable =65k+10k+5k=80k
        self.assertEqual(b.year_taxable_income, 80_000)

    def test_scotland_region(self):
        rUK = SoleTraderCalculator.calculate(500, 240)
        sco = SoleTraderCalculator.calculate(500, 240, region="scotland")
        self.assertEqual(sco.inputs["region"], "scotland")
        assert sco.income_tax is not None
        self.assertEqual(sco.income_tax.region, "scotland")
        # Scotland tax should differ at this income
        assert rUK.income_tax is not None
        self.assertNotEqual(sco.income_tax.total_tax, rUK.income_tax.total_tax)

    def test_student_loan_plan2(self):
        without = SoleTraderCalculator.calculate(500, 240)
        with_sl = SoleTraderCalculator.calculate(500, 240, student_loan_plan="plan2")
        self.assertIn("student_loan_plan", with_sl.inputs)
        self.assertIsNotNone(with_sl.student_loan)
        assert with_sl.student_loan is not None
        # plan2 threshold 29385, profit after pension 120k => above threshold
        self.assertGreater(with_sl.student_loan.repayment, 0)
        self.assertLess(with_sl.annual_take_home, without.annual_take_home)

    def test_postgraduate_loan_stacks(self):
        base = SoleTraderCalculator.calculate(500, 240, student_loan_plan="plan2")
        stacked = SoleTraderCalculator.calculate(
            500, 240, student_loan_plan="plan2", postgraduate_loan=True
        )
        self.assertIn("postgraduate_loan", stacked.inputs)
        self.assertLess(stacked.annual_take_home, base.annual_take_home)

    def test_20_day_take_home(self):
        b = SoleTraderCalculator.calculate(500, 240)
        self.assertEqual(b.display_take_home, round(b.annual_take_home / 240 * 20))


class TestSoleTraderConfig(unittest.TestCase):
    def test_load_sole_trader_mode_string_and_int(self):
        import json
        import tempfile
        import os
        from payday.config import load_config

        for mode in ("sole_trader", 4):
            data = {"mode": mode, "day_rate": 500}
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                json.dump(data, f)
                path = f.name
            try:
                cfg = load_config(path)
                assert cfg is not None
                self.assertEqual(cfg["mode"], mode)
            finally:
                os.unlink(path)

    def test_new_fields_roundtrip(self):
        import json
        import tempfile
        import os
        from payday.config import load_config

        data = {
            "mode": "sole_trader",
            "business_expenses": 5000,
            "personal_pension": 10000,
            "existing_self_employment": 7000,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            cfg = load_config(path)
            assert cfg is not None
            self.assertEqual(cfg["business_expenses"], 5000)
            self.assertEqual(cfg["personal_pension"], 10000)
            self.assertEqual(cfg["existing_self_employment"], 7000)
        finally:
            os.unlink(path)

    def test_invalid_mode_5_rejected(self):
        import json
        import tempfile
        import os
        from payday.config import load_config

        data = {"mode": 5}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)


class TestSoleTraderCLI(unittest.TestCase):
    def test_select_mode_sole_trader(self):
        from payday.cli import select_mode

        self.assertEqual(select_mode({"mode": "sole_trader"}), 4)
        self.assertEqual(select_mode({"mode": 4}), 4)

    def test_run_once_sole_trader_config(self):
        from unittest.mock import patch
        from io import StringIO
        from payday.cli import run_once
        from payday.models import SalaryBreakdown

        with patch("payday.cli.SoleTraderCalculator.calculate") as mock_calc:
            mock_calc.return_value = SalaryBreakdown(
                mode="Sole Trader",
                inputs={},
                steps=[],
                annual_take_home=0,
                display_take_home=0,
            )
            config = {
                "mode": "sole_trader",
                "day_rate": 400,
                "business_expenses": 2000,
                "personal_pension": 3000,
                "start_month": True,
                "existing_income": True,
                "existing_self_employment": True,
                "days_off": 25,
                "working_days": 200,
            }
            with patch("sys.stdout", new_callable=StringIO):
                with patch(
                    "builtins.input",
                    side_effect=lambda x: self.fail(f"unexpected prompt {x}"),
                ):
                    # Should not prompt
                    pass
                # run_once with mocked input that should not be called
                with patch(
                    "builtins.input", side_effect=Exception("unexpected prompt")
                ):
                    try:
                        run_once(config)
                    except Exception as e:
                        if "unexpected prompt" in str(e):
                            self.fail(f"run_once prompted unexpectedly: {e}")
                        raise
            mock_calc.assert_called_once()
            _, kwargs = mock_calc.call_args
            self.assertEqual(kwargs.get("business_expenses"), 2000)
            self.assertEqual(kwargs.get("personal_pension"), 3000)


class TestSoleTraderFormatter(unittest.TestCase):
    def test_sole_trader_title_and_turnover_context(self):
        from payday.models import SalaryBreakdown, StepLine
        from payday.formatters import format_breakdown

        steps = [
            StepLine("Turnover", 120000),
            StepLine("Trading Profit", 120000, is_subtotal=True),
        ]
        b = SalaryBreakdown(
            mode="Sole Trader",
            inputs={"day_rate": 500, "working_days": 240},
            steps=steps,
            annual_take_home=0,
            display_take_home=0,
        )
        out = format_breakdown(b)
        self.assertIn("Sole Trader (Self-Employed)", out)
        self.assertIn("(£500/day × 240 days)", out)

    def test_scotland_suffix(self):
        from payday.models import SalaryBreakdown
        from payday.formatters import format_breakdown

        b = SalaryBreakdown(
            mode="Sole Trader",
            inputs={"day_rate": 500, "working_days": 240, "region": "scotland"},
            steps=[],
            annual_take_home=0,
            display_take_home=0,
        )
        self.assertIn("[Scotland]", format_breakdown(b))


if __name__ == "__main__":
    unittest.main()
