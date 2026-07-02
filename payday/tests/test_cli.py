import unittest
from unittest.mock import patch
from io import StringIO
from payday.cli import (
    prompt_int,
    prompt_existing_income,
    prompt_salary_sacrifice,
    prompt_working_days,
    run_once,
)


class TestCLI(unittest.TestCase):
    @patch("builtins.input", side_effect=["42"])
    def test_prompt_int_valid(self, mock_input):
        result = prompt_int("Enter number")
        self.assertEqual(result, 42)

    @patch("builtins.input", side_effect=[""])
    def test_prompt_int_default(self, mock_input):
        result = prompt_int("Enter number", default=240)
        self.assertEqual(result, 240)

    @patch("builtins.input", side_effect=["5", "15"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_int_min_bound(self, mock_stdout, mock_input):
        # First input 5 is < 10, second input 15 is valid
        result = prompt_int("Enter number", min_val=10)
        self.assertEqual(result, 15)
        self.assertIn("Error: Value must be at least 10", mock_stdout.getvalue())

    @patch("builtins.input", side_effect=["25", "15"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_int_max_bound(self, mock_stdout, mock_input):
        # First input 25 is > 20, second input 15 is valid
        result = prompt_int("Enter number", max_val=20)
        self.assertEqual(result, 15)
        self.assertIn("Error: Value must be no more 20", mock_stdout.getvalue())

    @patch("builtins.input", side_effect=["abc", "123"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_int_non_integer(self, mock_stdout, mock_input):
        result = prompt_int("Enter number")
        self.assertEqual(result, 123)
        self.assertIn("Error: Please enter a whole number", mock_stdout.getvalue())

    @patch("builtins.input", side_effect=["", "99"])
    def test_prompt_int_no_default_retry(self, mock_input):
        # Empty input with no default should retry
        result = prompt_int("Enter number")
        self.assertEqual(result, 99)
        self.assertEqual(mock_input.call_count, 2)

    # ── prompt_existing_income tests ───────────────────────────────────

    def test_prompt_existing_income_full_year_returns_zero(self):
        """Full year (start_month=None) never prompts."""
        result = prompt_existing_income(None)
        self.assertEqual(result, 0)

    @patch("builtins.input", side_effect=["30000"])
    def test_prompt_existing_income_partial_year(self, mock_input):
        """Partial year prompts and returns entered value."""
        result = prompt_existing_income(8)
        self.assertEqual(result, 30000)

    @patch("builtins.input", side_effect=[""])
    def test_prompt_existing_income_defaults_to_zero(self, mock_input):
        """Partial year with empty input defaults to 0."""
        result = prompt_existing_income(8)
        self.assertEqual(result, 0)

    # ── prompt_existing_dividends tests ──────────────────────────────────

    def test_prompt_existing_dividends_full_year_returns_zero(self):
        """Full year (start_month=None) never prompts."""
        from payday.cli import prompt_existing_dividends
        result = prompt_existing_dividends(None)
        self.assertEqual(result, 0)

    @patch("builtins.input", side_effect=["15000"])
    def test_prompt_existing_dividends_partial_year(self, mock_input):
        """Partial year prompts and returns entered value."""
        from payday.cli import prompt_existing_dividends
        result = prompt_existing_dividends(8)
        self.assertEqual(result, 15000)

    @patch("builtins.input", side_effect=[""])
    def test_prompt_existing_dividends_defaults_to_zero(self, mock_input):
        """Partial year with empty input defaults to 0."""
        from payday.cli import prompt_existing_dividends
        result = prompt_existing_dividends(8)
        self.assertEqual(result, 0)

    # ── prompt_salary_sacrifice — y/n / manual amount tests ────────────

    @patch("builtins.input", side_effect=["n"])
    def test_salary_sacrifice_no_lowercase(self, mock_input):
        """Entering 'n' returns 0."""
        result = prompt_salary_sacrifice(0)
        self.assertEqual(result, 0)

    @patch("builtins.input", side_effect=["N"])
    def test_salary_sacrifice_no_uppercase(self, mock_input):
        """Entering 'N' returns 0."""
        result = prompt_salary_sacrifice(0)
        self.assertEqual(result, 0)

    @patch("builtins.input", side_effect=[""])
    def test_salary_sacrifice_default_no(self, mock_input):
        """Empty input returns 0 (defaults to no)."""
        result = prompt_salary_sacrifice(0)
        self.assertEqual(result, 0)

    @patch("builtins.input", side_effect=["y", "5000"])
    def test_salary_sacrifice_yes_with_amount(self, mock_input):
        """Entering 'y' then a monthly amount; result is annual (×12)."""
        result = prompt_salary_sacrifice(150_000)
        self.assertEqual(result, 60000)  # 5000 × 12

    @patch("builtins.input", side_effect=["y", "abc", "3000"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_salary_sacrifice_retry_on_invalid(self, mock_stdout, mock_input):
        """Entering non-numeric amount retries and accepts valid input."""
        result = prompt_salary_sacrifice(150_000)
        self.assertEqual(result, 36000)  # 3000 × 12
        self.assertIn("Error: Please enter a whole number", mock_stdout.getvalue())

    @patch("builtins.input", side_effect=["yes"])
    def test_salary_sacrifice_not_strict_y(self, mock_input):
        """'yes' is not 'y', so it returns 0 (only bare 'y' counts)."""
        result = prompt_salary_sacrifice(0)
        self.assertEqual(result, 0)

    @patch("builtins.input", side_effect=["y", "4350"])
    def test_salary_sacrifice_partial_year(self, mock_input):
        """Partial-year contract: monthly sacrifice × contract months, not 12."""
        result = prompt_salary_sacrifice(0, start_month=8)
        self.assertEqual(result, 34800)  # 4350 × 8, not 4350 × 12

    # ── prompt_salary_sacrifice — auto-calc tests ──────────────────────

    @patch("builtins.input", side_effect=["y", "", ""])
    @patch("sys.stdout", new_callable=StringIO)
    def test_salary_sacrifice_auto_calc_paye(self, mock_stdout, mock_input):
        """ENTER on amount → auto-calc mode: 150k with default cap → 50k/yr."""
        result = prompt_salary_sacrifice(150_000, mode="paye")
        self.assertEqual(result, 50_000)
        output = mock_stdout.getvalue()
        self.assertIn("Auto-calculated", output)
        self.assertIn("£50,000/yr", output)
        self.assertIn("£4,166/mo", output)

    @patch("builtins.input", side_effect=["y", "", ""])
    @patch("sys.stdout", new_callable=StringIO)
    def test_salary_sacrifice_auto_calc_below_cap(self, mock_stdout, mock_input):
        """Auto-calc when gross is already below cap: prints info and returns 0."""
        result = prompt_salary_sacrifice(50_000, mode="paye")
        self.assertEqual(result, 0)
        output = mock_stdout.getvalue()
        self.assertIn("already at or below the cap", output)

    @patch("builtins.input", side_effect=["y", "", "80000"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_salary_sacrifice_auto_calc_custom_cap(self, mock_stdout, mock_input):
        """Auto-calc with a custom cap of £80k instead of default £100k."""
        result = prompt_salary_sacrifice(130_000, mode="paye")
        self.assertEqual(result, 50_000)

    @patch("builtins.input", side_effect=["y", "", ""])
    @patch("sys.stdout", new_callable=StringIO)
    def test_salary_sacrifice_auto_calc_inside_ir35(self, mock_stdout, mock_input):
        """Auto-calc for Inside IR35: 144k assignment, 1200 margin, 100k cap."""
        result = prompt_salary_sacrifice(
            144_000,
            mode="inside_ir35",
            annual_margin=1200,
        )
        self.assertEqual(result, 28_050)
        output = mock_stdout.getvalue()
        self.assertIn("Auto-calculated", output)


    # ── run_once — mode 3 external IR35 tests ──────────────────────────

    @patch("payday.cli.OutsideIR35Calculator.calculate")
    @patch("builtins.input", side_effect=[
        "3",       # mode: Outside IR35
        "500",     # day rate
        "8",       # start month (Aug → partial year)
        "20000",   # existing income
        "15000",   # existing dividends
        "",        # days off (default 25)
        "",        # accept default working days
    ])
    @patch("sys.stdout", new_callable=StringIO)
    def test_run_once_mode3_passes_existing_dividends(
        self, mock_stdout, mock_input, mock_calc
    ):
        """Mode 3 should prompt for existing dividends and pass them to the calculator."""
        from payday.models import SalaryBreakdown
        mock_calc.return_value = SalaryBreakdown(
            mode="Outside IR35", inputs={}, steps=[], annual_take_home=0, display_take_home=0,
        )
        run_once()
        mock_calc.assert_called_once()
        _, kwargs = mock_calc.call_args
        self.assertIn("existing_dividends", kwargs)
        self.assertEqual(kwargs["existing_dividends"], 15000)

    @patch("payday.cli.OutsideIR35Calculator.calculate")
    @patch("builtins.input", side_effect=[
        "3",       # mode: Outside IR35
        "500",     # day rate
        "",        # start month (full year → no existing prompts)
        "",        # days off (default 25)
        "",        # accept default working days
    ])
    @patch("sys.stdout", new_callable=StringIO)
    def test_run_once_mode3_skips_existing_dividends_for_full_year(
        self, mock_stdout, mock_input, mock_calc
    ):
        """Full year (no start_month) should skip the existing dividends prompt entirely."""
        from payday.models import SalaryBreakdown
        mock_calc.return_value = SalaryBreakdown(
            mode="Outside IR35", inputs={}, steps=[], annual_take_home=0, display_take_home=0,
        )
        run_once()
        mock_calc.assert_called_once()
        _, kwargs = mock_calc.call_args
        self.assertEqual(kwargs.get("existing_dividends"), 0)


class TestPromptWorkingDays(unittest.TestCase):
    @patch("builtins.input", side_effect=["", ""])
    @patch("sys.stdout", new_callable=StringIO)
    def test_full_year_defaults(self, mock_stdout, mock_input):
        """Full year: 252 available, default 25 days-off → 227 net, accept."""
        result, days_off = prompt_working_days(None)
        self.assertEqual(result, 227)
        self.assertEqual(days_off, 25)
        output = mock_stdout.getvalue()
        self.assertIn("252", output)

    @patch("builtins.input", side_effect=["10", ""])
    @patch("sys.stdout", new_callable=StringIO)
    def test_full_year_custom_days_off(self, mock_stdout, mock_input):
        """Full year: 10 days-off → 242 net."""
        result, days_off = prompt_working_days(None)
        self.assertEqual(result, 242)
        self.assertEqual(days_off, 10)

    @patch("builtins.input", side_effect=["", "240"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_full_year_manual_override(self, mock_stdout, mock_input):
        """Override at final prompt: enter 240 instead of default 227."""
        result, days_off = prompt_working_days(None)
        self.assertEqual(result, 240)
        self.assertEqual(days_off, 25)

    @patch("builtins.input", side_effect=["", ""])
    @patch("sys.stdout", new_callable=StringIO)
    def test_august_start_shows_period_specific_count(self, mock_stdout, mock_input):
        """Aug start: 170 available, -25 → 145 net."""
        result, days_off = prompt_working_days(8)
        self.assertEqual(result, 145)
        output = mock_stdout.getvalue()
        self.assertIn("170", output)

    @patch("builtins.input", side_effect=["", "abc", "200"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_manual_override_invalid_then_valid(self, mock_stdout, mock_input):
        """Non-numeric override retries, then accepts 200."""
        result, days_off = prompt_working_days(None)
        self.assertEqual(result, 200)
        self.assertIn("Error: Please enter a whole number", mock_stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
