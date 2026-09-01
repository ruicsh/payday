import unittest
from unittest.mock import patch
from io import StringIO
from payday.cli import (
    prompt_int,
    prompt_float,
    prompt_existing_income,
    prompt_paystream,
    prompt_salary_sacrifice,
    prompt_working_days,
    run_once,
)


class TestCLI(unittest.TestCase):
    # ── select_mode config tests ───────────────────────────────────────

    @patch("builtins.input", side_effect=["3"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_select_mode_interactive(self, mock_stdout, mock_input):
        from payday.cli import select_mode

        result = select_mode()
        self.assertEqual(result, 3)

    def test_select_mode_config_paye(self):
        from payday.cli import select_mode

        result = select_mode({"mode": "paye"})
        self.assertEqual(result, 1)

    def test_select_mode_config_inside_ir35_string(self):
        from payday.cli import select_mode

        result = select_mode({"mode": "inside_ir35"})
        self.assertEqual(result, 2)

    def test_select_mode_config_outside_ir35_int(self):
        from payday.cli import select_mode

        result = select_mode({"mode": 3})
        self.assertEqual(result, 3)

    def test_select_mode_config_none_shows_menu(self):
        from payday.cli import select_mode

        with patch("builtins.input", return_value="2"):
            result = select_mode(None)
        self.assertEqual(result, 2)

    # ── prompt_int / prompt_float config tests ─────────────────────────

    def test_prompt_int_config_value(self):
        result = prompt_int("Enter number", config_value=42)
        self.assertEqual(result, 42)

    def test_prompt_int_config_value_default_ignored(self):
        result = prompt_int("Enter number", default=10, config_value=99)
        self.assertEqual(result, 99)

    def test_prompt_float_config_value(self):
        result = prompt_float("Enter amount", config_value=12345.67)
        self.assertEqual(result, 12345.67)

    def test_prompt_int_config_true_uses_default(self):
        result = prompt_int("Enter number", default=10, config_value=True)
        self.assertEqual(result, 10)

    def test_prompt_float_config_true_uses_default(self):
        result = prompt_float("Enter amount", default=5.5, config_value=True)
        self.assertEqual(result, 5.5)

    def test_prompt_int_config_value_raises_on_min_violation(self):
        with self.assertRaises(ValueError):
            prompt_int("Enter number", min_val=10, config_value=5)

    def test_prompt_int_config_value_raises_on_max_violation(self):
        with self.assertRaises(ValueError):
            prompt_int("Enter number", max_val=100, config_value=200)

    def test_prompt_float_config_value_raises_on_min_violation(self):
        with self.assertRaises(ValueError):
            prompt_float("Enter amount", min_val=1.0, config_value=0.0)

    def test_prompt_float_config_value_raises_on_max_violation(self):
        with self.assertRaises(ValueError):
            prompt_float("Enter amount", max_val=10.0, config_value=20.0)

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_int_config_true_prints_message(self, mock_stdout):
        prompt_int("Enter number", default=10, config_value=True)
        output = mock_stdout.getvalue()
        self.assertIn("Enter number [10]: 10", output)

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_float_config_true_prints_message(self, mock_stdout):
        prompt_float("Enter amount", default=5.5, config_value=True)
        output = mock_stdout.getvalue()
        self.assertIn("Enter amount [5.5]: 5.5", output)

    # ── prompt_start_month / prompt_existing_* config tests ────────────

    def test_prompt_start_month_config(self):
        from payday.cli import prompt_start_month

        result = prompt_start_month(config={"start_month": 4})
        self.assertEqual(result, 4)

    def test_prompt_start_month_config_out_of_range_raises(self):
        from payday.cli import prompt_start_month

        with self.assertRaises(ValueError):
            prompt_start_month(config={"start_month": 13})
        with self.assertRaises(ValueError):
            prompt_start_month(config={"start_month": 0})

    def test_prompt_start_month_config_true_default(self):
        from payday.cli import prompt_start_month

        result = prompt_start_month(config={"start_month": True})
        self.assertIsNone(result)

    @patch("builtins.input", return_value="5")
    def test_prompt_start_month_config_null_prompts(self, mock_input):
        from payday.cli import prompt_start_month

        result = prompt_start_month(config={"start_month": None})
        self.assertEqual(result, 5)
        mock_input.assert_called_once()

    def test_prompt_existing_income_config(self):
        result = prompt_existing_income(8, config={"existing_income": 30000})
        self.assertEqual(result, 30000)

    def test_prompt_existing_income_config_true_default(self):
        result = prompt_existing_income(8, config={"existing_income": True})
        self.assertEqual(result, 0)

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_existing_income_config_true_prints_message(self, mock_stdout):
        prompt_existing_income(8, config={"existing_income": True})
        output = mock_stdout.getvalue()
        self.assertIn(
            "Existing employment income already earned this tax year (£) [0]: 0", output
        )

    @patch("builtins.input", return_value="3000")
    def test_prompt_existing_income_config_null_prompts(self, mock_input):
        result = prompt_existing_income(8, config={"existing_income": None})
        self.assertEqual(result, 3000)

    def test_prompt_existing_dividends_config(self):
        from payday.cli import prompt_existing_dividends

        result = prompt_existing_dividends(8, config={"existing_dividends": 15000})
        self.assertEqual(result, 15000)

    def test_prompt_existing_dividends_config_true_default(self):
        from payday.cli import prompt_existing_dividends

        result = prompt_existing_dividends(8, config={"existing_dividends": True})
        self.assertEqual(result, 0)

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_existing_dividends_config_true_prints_message(self, mock_stdout):
        from payday.cli import prompt_existing_dividends

        prompt_existing_dividends(8, config={"existing_dividends": True})
        output = mock_stdout.getvalue()
        self.assertIn(
            "Existing dividends already received this tax year (£) [0]: 0", output
        )

    @patch("builtins.input", return_value="5000")
    def test_prompt_existing_dividends_config_null_prompts(self, mock_input):
        from payday.cli import prompt_existing_dividends

        result = prompt_existing_dividends(8, config={"existing_dividends": None})
        self.assertEqual(result, 5000)

    # ── prompt_salary_sacrifice config tests ───────────────────────────

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_salary_sacrifice_config_disabled(self, mock_stdout):
        config = {"salary_sacrifice_enabled": False}
        result = prompt_salary_sacrifice(100_000, config=config)
        self.assertEqual(result, 0)

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_salary_sacrifice_config_manual(self, mock_stdout):
        config = {"salary_sacrifice_enabled": True, "monthly_salary_sacrifice": 2000}
        result = prompt_salary_sacrifice(100_000, config=config)
        self.assertEqual(result, 24000)

    # ── prompt_salary_sacrifice daily config tests ────────────────────

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_salary_sacrifice_daily_manual(self, mock_stdout):
        config = {"salary_sacrifice_enabled": True, "daily_salary_sacrifice": 50}
        result = prompt_salary_sacrifice(
            150_000,
            mode="inside_ir35",
            working_days=227,
            is_paystream=True,
            config=config,
        )
        self.assertEqual(result, 50 * 227)

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_salary_sacrifice_daily_capped_at_60k(self, mock_stdout):
        config = {"salary_sacrifice_enabled": True, "daily_salary_sacrifice": 300}
        result = prompt_salary_sacrifice(
            150_000,
            mode="inside_ir35",
            working_days=227,
            is_paystream=True,
            config=config,
        )
        self.assertEqual(result, 60_000)

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_salary_sacrifice_daily_requires_paystream(self, mock_stdout):
        config = {"salary_sacrifice_enabled": True, "daily_salary_sacrifice": 50}
        with self.assertRaises(ValueError):
            prompt_salary_sacrifice(
                150_000,
                mode="inside_ir35",
                working_days=227,
                is_paystream=False,
                config=config,
            )

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_salary_sacrifice_daily_requires_working_days(self, mock_stdout):
        config = {"salary_sacrifice_enabled": True, "daily_salary_sacrifice": 50}
        with self.assertRaises(ValueError):
            prompt_salary_sacrifice(
                150_000,
                mode="inside_ir35",
                is_paystream=True,
                config=config,
            )

    @patch("builtins.input", side_effect=[""])
    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_salary_sacrifice_daily_auto(self, mock_stdout, mock_input):
        config = {
            "salary_sacrifice_enabled": True,
            "daily_salary_sacrifice": "auto",
            "income_target": False,
        }
        result = prompt_salary_sacrifice(
            150_000,
            mode="inside_ir35",
            annual_margin=5_000,
            admin_charge=1_000,
            is_paystream=True,
            config=config,
        )
        self.assertEqual(result, 60_000)
        mock_input.assert_not_called()
        output = mock_stdout.getvalue()
        self.assertIn("Daily salary sacrifice", output)

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_salary_sacrifice_daily_max(self, mock_stdout):
        config = {"salary_sacrifice_enabled": True, "daily_salary_sacrifice": "max"}
        result = prompt_salary_sacrifice(
            150_000,
            mode="inside_ir35",
            annual_margin=5_000,
            admin_charge=1_000,
            is_paystream=True,
            config=config,
        )
        self.assertEqual(result, 60_000)

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_salary_sacrifice_daily_true_triggers_auto(self, mock_stdout):
        config = {
            "salary_sacrifice_enabled": True,
            "daily_salary_sacrifice": True,
            "income_target": False,
        }
        result = prompt_salary_sacrifice(
            150_000,
            mode="inside_ir35",
            annual_margin=5_000,
            admin_charge=1_000,
            is_paystream=True,
            config=config,
        )
        self.assertEqual(result, 60_000)

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_salary_sacrifice_both_monthly_and_daily_conflict(self, mock_stdout):
        config = {
            "salary_sacrifice_enabled": True,
            "monthly_salary_sacrifice": 2000,
            "daily_salary_sacrifice": 50,
        }
        with self.assertRaises(ValueError):
            prompt_salary_sacrifice(
                150_000,
                mode="inside_ir35",
                working_days=227,
                is_paystream=True,
                config=config,
            )

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_salary_sacrifice_config_max(self, mock_stdout):
        config = {"salary_sacrifice_enabled": True, "monthly_salary_sacrifice": "max"}
        result = prompt_salary_sacrifice(150_000, config=config)
        self.assertEqual(result, 60_000)

    @patch("builtins.input", side_effect=[""])
    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_salary_sacrifice_config_auto(self, mock_stdout, mock_input):
        config = {"salary_sacrifice_enabled": True, "monthly_salary_sacrifice": "auto"}
        result = prompt_salary_sacrifice(150_000, config=config)
        self.assertEqual(result, 50_000)

    @patch("builtins.input", side_effect=[""])
    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_salary_sacrifice_config_true_triggers_auto(
        self, mock_stdout, mock_input
    ):
        config = {"salary_sacrifice_enabled": True, "monthly_salary_sacrifice": True}
        result = prompt_salary_sacrifice(150_000, config=config)
        self.assertEqual(result, 50_000)
        output = mock_stdout.getvalue()
        self.assertIn("auto", output)

    @patch("builtins.input", side_effect=[""])
    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_salary_sacrifice_config_auto_with_cap_true(
        self, mock_stdout, mock_input
    ):
        config = {
            "salary_sacrifice_enabled": True,
            "monthly_salary_sacrifice": "auto",
            "income_target": True,
        }
        result = prompt_salary_sacrifice(150_000, config=config)
        self.assertEqual(result, 50_000)
        mock_input.assert_called_once_with("Taxable income cap [£100,000]: ")

    @patch("builtins.input", side_effect=["80000"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_salary_sacrifice_config_auto_cap_none_prompts(
        self, mock_stdout, mock_input
    ):
        """Config with monthly_salary_sacrifice='auto' and no cap should prompt."""
        config = {
            "salary_sacrifice_enabled": True,
            "monthly_salary_sacrifice": "auto",
        }
        result = prompt_salary_sacrifice(150_000, config=config)
        self.assertEqual(result, 60_000)
        mock_input.assert_called_once_with("Taxable income cap [£100,000]: ")

    @patch("builtins.input", side_effect=[""])
    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_salary_sacrifice_config_auto_no_target_paye(
        self, mock_stdout, mock_input
    ):
        """income_target=false with auto should max out pension (no prompt)."""
        config = {
            "salary_sacrifice_enabled": True,
            "monthly_salary_sacrifice": "auto",
            "income_target": False,
        }
        result = prompt_salary_sacrifice(150_000, config=config)
        self.assertEqual(result, 60_000)
        mock_input.assert_not_called()
        output = mock_stdout.getvalue()
        self.assertIn("Income target: none", output)

    @patch("builtins.input", side_effect=[""])
    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_salary_sacrifice_config_auto_no_target_inside_ir35(
        self, mock_stdout, mock_input
    ):
        """income_target=false with auto should max out within budget (IR35)."""
        config = {
            "salary_sacrifice_enabled": True,
            "monthly_salary_sacrifice": "auto",
            "income_target": False,
        }
        result = prompt_salary_sacrifice(
            150_000,
            mode="inside_ir35",
            annual_margin=5_000,
            admin_charge=1_000,
            config=config,
        )
        self.assertEqual(result, 60_000)
        mock_input.assert_not_called()

    # ── prompt_paystream tests ─────────────────────────────────────────

    def test_prompt_paystream_config_true(self):
        result = prompt_paystream(config={"is_paystream": True})
        self.assertTrue(result)

    def test_prompt_paystream_config_false(self):
        result = prompt_paystream(config={"is_paystream": False})
        self.assertFalse(result)

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_paystream_config_true_prints_message(self, mock_stdout):
        prompt_paystream(config={"is_paystream": True})
        output = mock_stdout.getvalue()
        self.assertIn("Is your umbrella company PayStream? [y/N]: yes", output)

    @patch("builtins.input", return_value="y")
    def test_prompt_paystream_yes(self, mock_input):
        result = prompt_paystream()
        self.assertTrue(result)

    @patch("builtins.input", return_value="n")
    def test_prompt_paystream_no(self, mock_input):
        result = prompt_paystream()
        self.assertFalse(result)

    @patch("builtins.input", return_value="")
    def test_prompt_paystream_default_no(self, mock_input):
        result = prompt_paystream()
        self.assertFalse(result)

    # ── prompt_region tests ────────────────────────────────────────────

    @patch("builtins.input", return_value="y")
    def test_prompt_region_yes(self, mock_input):
        from payday.cli import prompt_region

        self.assertEqual(prompt_region(), "scotland")

    @patch("builtins.input", return_value="n")
    def test_prompt_region_no(self, mock_input):
        from payday.cli import prompt_region

        self.assertEqual(prompt_region(), "rest_of_uk")

    @patch("builtins.input", return_value="")
    def test_prompt_region_default_no(self, mock_input):
        from payday.cli import prompt_region

        self.assertEqual(prompt_region(), "rest_of_uk")

    def test_prompt_region_config_scotland(self):
        from payday.cli import prompt_region

        with patch("sys.stdout", new_callable=StringIO):
            self.assertEqual(prompt_region(config={"region": "scotland"}), "scotland")

    def test_prompt_region_config_alias_normalises(self):
        from payday.cli import prompt_region

        for alias in ("england", "wales", "northern_ireland", "rest_of_uk"):
            with patch("sys.stdout", new_callable=StringIO):
                self.assertEqual(prompt_region(config={"region": alias}), "rest_of_uk")

    def test_prompt_region_config_absent_defaults(self):
        from payday.cli import prompt_region

        self.assertEqual(prompt_region(config={"region": None}), "rest_of_uk")
        self.assertEqual(prompt_region(config={}), "rest_of_uk")

    # ── prompt_working_days config tests ───────────────────────────────

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_working_days_config_days_off(self, mock_stdout):
        from payday.cli import prompt_working_days

        result, days_off = prompt_working_days(None, config={"days_off": 10})
        self.assertEqual(days_off, 10)
        self.assertEqual(result, 242)

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_working_days_config_override(self, mock_stdout):
        from payday.cli import prompt_working_days

        result, days_off = prompt_working_days(
            None, config={"days_off": 10, "working_days": 200}
        )
        self.assertEqual(days_off, 10)
        self.assertEqual(result, 200)

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_working_days_config_days_off_true(self, mock_stdout):
        from payday.cli import prompt_working_days

        result, days_off = prompt_working_days(None, config={"days_off": True})
        self.assertEqual(days_off, 25)
        self.assertEqual(result, 227)

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_working_days_config_working_days_true(self, mock_stdout):
        from payday.cli import prompt_working_days

        result, days_off = prompt_working_days(None, config={"working_days": True})
        self.assertEqual(days_off, 25)
        self.assertEqual(result, 227)
        output = mock_stdout.getvalue()
        self.assertIn(
            "Days off you'll take (annual leave, sick, etc.) [25]: 25", output
        )

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_working_days_config_override_no_days_off(self, mock_stdout):
        """Explicit working_days with absent days_off should default to 25."""
        from payday.cli import prompt_working_days

        result, days_off = prompt_working_days(None, config={"working_days": 200})
        self.assertEqual(result, 200)
        self.assertEqual(days_off, 25)

    @patch("sys.stdout", new_callable=StringIO)
    def test_prompt_working_days_config_working_days_true_with_days_off(
        self, mock_stdout
    ):
        from payday.cli import prompt_working_days

        result, days_off = prompt_working_days(
            None, config={"working_days": True, "days_off": 10}
        )
        self.assertEqual(days_off, 10)
        self.assertEqual(result, 242)

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

    @patch("builtins.input", side_effect=["y", "6001"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_salary_sacrifice_manual_capped_at_60k(self, mock_stdout, mock_input):
        """Monthly amount exceeding £60k/yr gets capped at £60k with warning."""
        result = prompt_salary_sacrifice(150_000)
        self.assertEqual(result, 60_000)
        self.assertIn("capped", mock_stdout.getvalue())

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

    @patch("builtins.input", side_effect=["y", "", "", ""])
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

    @patch("builtins.input", side_effect=["y", "", ""])
    @patch("sys.stdout", new_callable=StringIO)
    def test_salary_sacrifice_auto_calc_capped_at_60k(self, mock_stdout, mock_input):
        """Auto-calc: 300k gross, 100k cap → capped at £60k with warning."""
        result = prompt_salary_sacrifice(300_000, mode="paye")
        self.assertEqual(result, 60_000)
        output = mock_stdout.getvalue()
        self.assertIn("capped", output)

    # ── prompt_salary_sacrifice — "max" keyword tests ─────────────────

    @patch("builtins.input", side_effect=["y", "max"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_salary_sacrifice_max_paye(self, mock_stdout, mock_input):
        """Typing 'max' on PAYE with salary > 60k returns 60k (the cap)."""
        result = prompt_salary_sacrifice(150_000, mode="paye")
        self.assertEqual(result, 60_000)
        output = mock_stdout.getvalue()
        self.assertIn("Maximum sacrifice", output)
        self.assertIn("£60,000/yr", output)
        self.assertIn("£5,000/mo", output)

    @patch("builtins.input", side_effect=["y", "max"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_salary_sacrifice_max_paye_below_cap(self, mock_stdout, mock_input):
        """Typing 'max' on PAYE with salary < 60k returns the full salary."""
        result = prompt_salary_sacrifice(30_000, mode="paye")
        self.assertEqual(result, 30_000)
        output = mock_stdout.getvalue()
        self.assertIn("Maximum sacrifice", output)

    @patch("builtins.input", side_effect=["y", "MAX"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_salary_sacrifice_max_case_insensitive(self, mock_stdout, mock_input):
        """Typing 'MAX' (uppercase) also triggers max mode."""
        result = prompt_salary_sacrifice(150_000, mode="paye")
        self.assertEqual(result, 60_000)

    @patch("builtins.input", side_effect=["y", "", "max"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_salary_sacrifice_max_inside_ir35(self, mock_stdout, mock_input):
        """Typing 'max' on Inside IR35 with enough budget returns 60k."""
        result = prompt_salary_sacrifice(
            144_000, mode="inside_ir35", annual_margin=1200
        )
        self.assertEqual(result, 60_000)
        output = mock_stdout.getvalue()
        self.assertIn("Maximum sacrifice", output)

    @patch("builtins.input", side_effect=["y", "max"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_salary_sacrifice_max_partial_year(self, mock_stdout, mock_input):
        """Partial-year contract: annual max still 60k, monthly = 60k / contract_months."""
        result = prompt_salary_sacrifice(150_000, mode="paye", start_month=8)
        self.assertEqual(result, 60_000)
        output = mock_stdout.getvalue()
        self.assertIn("£7,500/mo", output)  # 60000 / 8 = 7500

    # ── prompt_salary_sacrifice — manual daily tests ─────────────────────

    @patch("builtins.input", side_effect=["y", "d", "50"])
    def test_salary_sacrifice_manual_daily_amount(self, mock_input):
        """Manual daily: y → daily → 50/day × 227 days = annual."""
        result = prompt_salary_sacrifice(150_000, mode="inside_ir35", working_days=227)
        self.assertEqual(result, 50 * 227)
        self.assertEqual(result.frequency, "daily")

    @patch("builtins.input", side_effect=["y", "d", "100"])
    def test_salary_sacrifice_manual_daily_generic_umbrella(self, mock_input):
        """Manual daily works for any Inside IR35 umbrella, not just PayStream."""
        result = prompt_salary_sacrifice(
            150_000,
            mode="inside_ir35",
            working_days=227,
            is_paystream=False,
        )
        self.assertEqual(result, 100 * 227)
        self.assertEqual(result.frequency, "daily")

    @patch("builtins.input", side_effect=["y", "d", "500"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_salary_sacrifice_manual_daily_capped_at_60k(self, mock_stdout, mock_input):
        """Daily amount exceeding £60k/yr is capped with per-day warning."""
        result = prompt_salary_sacrifice(150_000, mode="inside_ir35", working_days=227)
        self.assertEqual(result, 60_000)
        self.assertEqual(result.frequency, "daily")
        output = mock_stdout.getvalue()
        self.assertIn("capped", output)
        self.assertIn("/day", output)

    @patch("builtins.input", side_effect=["y", "d", "max"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_salary_sacrifice_manual_daily_max(self, mock_stdout, mock_input):
        """Max with daily frequency returns 60k and shows per-day figure."""
        result = prompt_salary_sacrifice(
            150_000,
            mode="inside_ir35",
            working_days=227,
            annual_margin=5_000,
            admin_charge=1_000,
        )
        self.assertEqual(result, 60_000)
        self.assertEqual(result.frequency, "daily")
        output = mock_stdout.getvalue()
        self.assertIn("Maximum sacrifice", output)
        self.assertIn("/day", output)

    @patch("builtins.input", side_effect=["y", "d", "", ""])
    @patch("sys.stdout", new_callable=StringIO)
    def test_salary_sacrifice_manual_daily_auto(self, mock_stdout, mock_input):
        """Auto with daily frequency calculates correctly and shows per-day."""
        result = prompt_salary_sacrifice(
            144_000,
            mode="inside_ir35",
            annual_margin=1_200,
            working_days=227,
        )
        # 144k assignment, 1.2k margin, 100k cap → known annual 28,050
        self.assertEqual(result, 28_050)
        self.assertEqual(result.frequency, "daily")
        output = mock_stdout.getvalue()
        self.assertIn("Auto-calculated", output)
        self.assertIn("/day", output)

    @patch("builtins.input", side_effect=["y", "m", "2000"])
    def test_salary_sacrifice_manual_monthly_explicit(self, mock_input):
        """Explicit monthly choice: y → monthly → 2000/mo × 12 = annual."""
        result = prompt_salary_sacrifice(150_000, mode="inside_ir35", working_days=227)
        self.assertEqual(result, 2000 * 12)
        self.assertEqual(result.frequency, "monthly")

    @patch("builtins.input", side_effect=["y", "", "2000"])
    def test_salary_sacrifice_manual_empty_frequency_defaults_monthly(self, mock_input):
        """Empty frequency input defaults to monthly."""
        result = prompt_salary_sacrifice(150_000, mode="inside_ir35", working_days=227)
        self.assertEqual(result, 2000 * 12)
        self.assertEqual(result.frequency, "monthly")

    @patch("builtins.input", side_effect=["y", "x", "d", "50"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_salary_sacrifice_manual_daily_invalid_frequency_retry(
        self, mock_stdout, mock_input
    ):
        """Invalid frequency input retries until valid daily."""
        result = prompt_salary_sacrifice(150_000, mode="inside_ir35", working_days=227)
        self.assertEqual(result, 50 * 227)
        self.assertEqual(result.frequency, "daily")
        output = mock_stdout.getvalue()
        self.assertIn("Error: Enter 'm' for monthly or 'd' for daily.", output)

    @patch("builtins.input", side_effect=["y", "d"])
    def test_salary_sacrifice_manual_daily_requires_working_days(self, mock_input):
        """Daily manual without working_days raises ValueError."""
        with self.assertRaises(ValueError):
            prompt_salary_sacrifice(150_000, mode="inside_ir35", working_days=None)

    def test_sacrifice_choice_is_int_subclass(self):
        """SacrificeChoice behaves as int while carrying frequency."""
        from payday.cli import SacrificeChoice

        choice = SacrificeChoice(50_000, "daily")
        self.assertEqual(choice, 50_000)
        self.assertEqual(choice.frequency, "daily")
        self.assertIsInstance(choice, int)
        daily = SacrificeChoice(10 * 227, "daily")
        self.assertEqual(int(daily), 10 * 227)
        self.assertEqual(SacrificeChoice(2000 * 12, "monthly").frequency, "monthly")

    @patch("builtins.input", side_effect=["y", "5000"])
    def test_salary_sacrifice_paye_manual_no_frequency_prompt(self, mock_input):
        """PAYE manual path does not prompt for daily/monthly frequency."""
        result = prompt_salary_sacrifice(150_000, mode="paye")
        self.assertEqual(result, 5000 * 12)
        self.assertEqual(result.frequency, "monthly")
        # Only two prompts: y/N and amount — ensure no extra call
        self.assertEqual(mock_input.call_count, 2)

    # ── run_once — mode 3 external IR35 tests ──────────────────────────

    @patch("payday.cli.OutsideIR35Calculator.calculate")
    @patch(
        "builtins.input",
        side_effect=[
            "3",  # mode: Outside IR35
            "500",  # day rate
            "8",  # start month (Aug → partial year)
            "20000",  # existing income
            "15000",  # existing dividends
            "",  # days off (default 25)
            "",  # accept default working days
            "",  # director pension (default 0)
        ],
    )
    @patch("sys.stdout", new_callable=StringIO)
    def test_run_once_mode3_passes_existing_dividends(
        self, mock_stdout, mock_input, mock_calc
    ):
        """Mode 3 should prompt for existing dividends and pass them to the calculator."""
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
        self.assertIn("existing_dividends", kwargs)
        self.assertEqual(kwargs["existing_dividends"], 15000)

    @patch("payday.cli.OutsideIR35Calculator.calculate")
    @patch(
        "builtins.input",
        side_effect=[
            "3",  # mode: Outside IR35
            "500",  # day rate
            "",  # start month (full year → no existing prompts)
            "",  # days off (default 25)
            "",  # accept default working days
            "",  # director pension (default 0)
        ],
    )
    @patch("sys.stdout", new_callable=StringIO)
    def test_run_once_mode3_skips_existing_dividends_for_full_year(
        self, mock_stdout, mock_input, mock_calc
    ):
        """Full year (no start_month) should skip the existing dividends prompt entirely."""
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
        self.assertEqual(kwargs.get("existing_dividends"), 0)

    # ── run_once — full config (no prompts) tests ──────────────────────

    @patch("payday.cli.PAYECalculator.calculate")
    @patch("builtins.input", side_effect=["n"])  # only "run again?" prompt
    @patch("sys.stdout", new_callable=StringIO)
    def test_run_once_paye_full_config(self, mock_stdout, mock_input, mock_calc):
        """PAYE with full config should skip all prompts."""
        from payday.models import SalaryBreakdown

        mock_calc.return_value = SalaryBreakdown(
            mode="PAYE",
            inputs={},
            steps=[],
            annual_take_home=0,
            display_take_home=0,
        )
        config = {"mode": "paye", "salary": 50000, "salary_sacrifice_enabled": False}
        run_once(config)
        mock_calc.assert_called_once_with(
            50000, salary_sacrifice=0, region="rest_of_uk"
        )

    @patch("payday.cli.InsideIR35Calculator.calculate")
    @patch("builtins.input", side_effect=["n"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_run_once_inside_ir35_full_config(self, mock_stdout, mock_input, mock_calc):
        """Inside IR35 with full config should skip all prompts."""
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
            "day_rate": 600,
            "start_month": 4,
            "existing_income": 10000,
            "existing_dividends": 5000,
            "days_off": 25,
            "umbrella_margin": 25,
            "salary_sacrifice_enabled": False,
        }
        run_once(config)
        mock_calc.assert_called_once()
        kwargs = mock_calc.call_args[1] if len(mock_calc.call_args) > 1 else {}
        self.assertEqual(kwargs.get("existing_dividends"), 5000)

    @patch("payday.cli.InsideIR35Calculator.calculate")
    @patch("builtins.input")
    @patch("sys.stdout", new_callable=StringIO)
    def test_run_once_inside_ir35_config_salary_sacrifice(
        self, mock_stdout, mock_input, mock_calc
    ):
        """Inside IR35 config with salary sacrifice should use config value, not prompt."""
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
            "day_rate": 600,
            "start_month": 4,
            "existing_income": 10000,
            "existing_dividends": 5000,
            "days_off": 25,
            "umbrella_margin": 25,
            "is_paystream": True,
            "salary_sacrifice_enabled": True,
            "monthly_salary_sacrifice": 2000,
            "income_target": 60000,
        }
        run_once(config)
        mock_calc.assert_called_once()
        kwargs = mock_calc.call_args[1] if len(mock_calc.call_args) > 1 else {}
        self.assertEqual(kwargs.get("salary_sacrifice"), 24000)
        output = mock_stdout.getvalue()
        self.assertIn(
            "Monthly salary sacrifice [ENTER=auto, or 'max'] (£): 2000", output
        )
        # input() should NOT be called (no interactive prompts)
        mock_input.assert_not_called()

    @patch("payday.cli.OutsideIR35Calculator.calculate")
    @patch("builtins.input", side_effect=["n"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_run_once_outside_ir35_full_config(
        self, mock_stdout, mock_input, mock_calc
    ):
        """Outside IR35 with full config should skip all prompts."""
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
            "day_rate": 500,
            "start_month": True,
            "existing_income": True,
            "existing_dividends": True,
            "days_off": 25,
            "working_days": 200,
            "director_pension": True,
        }
        run_once(config)
        mock_calc.assert_called_once()

    @patch("payday.cli.OutsideIR35Calculator.calculate")
    @patch("builtins.input", side_effect=["n"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_run_once_outside_ir35_config_with_director_pension(
        self, mock_stdout, mock_input, mock_calc
    ):
        """Config with director_pension set passes value without prompting."""
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
            "day_rate": 500,
            "start_month": True,
            "existing_income": True,
            "existing_dividends": True,
            "days_off": 25,
            "working_days": 200,
            "director_pension": 25000,
        }
        run_once(config)
        mock_calc.assert_called_once()
        _, kwargs = mock_calc.call_args
        self.assertEqual(kwargs.get("director_pension"), 25000)
        # No interactive prompts (all values from config)
        self.assertEqual(mock_input.call_count, 0)

    # ── director_pension CLI tests ─────────────────────────────────────

    @patch("payday.cli.OutsideIR35Calculator.calculate")
    @patch(
        "builtins.input",
        side_effect=[
            "3",  # mode: Outside IR35
            "500",  # day rate
            "",  # start month (full year)
            "",  # days off (default 25)
            "",  # accept default working days
            "",  # director pension (default 0)
        ],
    )
    @patch("sys.stdout", new_callable=StringIO)
    def test_run_once_mode3_director_pension_default(
        self, mock_stdout, mock_input, mock_calc
    ):
        """Outside IR35: empty director pension prompt defaults to 0."""
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
        self.assertEqual(kwargs.get("director_pension"), 0)

    @patch("payday.cli.OutsideIR35Calculator.calculate")
    @patch(
        "builtins.input",
        side_effect=[
            "3",  # mode: Outside IR35
            "500",  # day rate
            "",  # start month (full year)
            "",  # days off (default 25)
            "",  # accept default working days
            "20000",  # director pension
        ],
    )
    @patch("sys.stdout", new_callable=StringIO)
    def test_run_once_mode3_director_pension_entered(
        self, mock_stdout, mock_input, mock_calc
    ):
        """Outside IR35: entered director pension is passed to calculator."""
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
        self.assertEqual(kwargs.get("director_pension"), 20000)

    @patch("payday.cli.OutsideIR35Calculator.calculate")
    @patch(
        "builtins.input",
        side_effect=[
            "3",  # mode: Outside IR35
            "500",  # day rate
            "",  # start month (full year)
            "",  # days off (default 25)
            "",  # accept default working days
            "60000",  # max director pension
        ],
    )
    @patch("sys.stdout", new_callable=StringIO)
    def test_run_once_mode3_director_pension_max(
        self, mock_stdout, mock_input, mock_calc
    ):
        """Outside IR35: max director pension (60000) passes through."""
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
        self.assertEqual(kwargs.get("director_pension"), 60000)


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
        result, _ = prompt_working_days(8)
        self.assertEqual(result, 145)
        output = mock_stdout.getvalue()
        self.assertIn("170", output)

    @patch("builtins.input", side_effect=["", "abc", "200"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_manual_override_invalid_then_valid(self, mock_stdout, mock_input):
        """Non-numeric override retries, then accepts 200."""
        result, _ = prompt_working_days(None)
        self.assertEqual(result, 200)
        self.assertIn("Error: Please enter a whole number", mock_stdout.getvalue())

    @patch("builtins.input", side_effect=["25", ""])
    @patch("sys.stdout", new_callable=StringIO)
    def test_march_start_clamps_to_one(self, mock_stdout, mock_input):
        """March: 24 available, 25 days-off → net clamped to 1 (not 0)."""
        result, days_off = prompt_working_days(3)
        self.assertEqual(result, 1)
        self.assertEqual(days_off, 25)


if __name__ == "__main__":
    unittest.main()
