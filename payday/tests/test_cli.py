import unittest
from unittest.mock import patch
from io import StringIO
from payday.cli import prompt_int, prompt_existing_income, prompt_salary_sacrifice


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

    # ── prompt_salary_sacrifice tests ───────────────────────────────────

    @patch("builtins.input", side_effect=["n"])
    def test_salary_sacrifice_no_lowercase(self, mock_input):
        """Entering 'n' returns 0."""
        result = prompt_salary_sacrifice()
        self.assertEqual(result, 0)

    @patch("builtins.input", side_effect=["N"])
    def test_salary_sacrifice_no_uppercase(self, mock_input):
        """Entering 'N' returns 0."""
        result = prompt_salary_sacrifice()
        self.assertEqual(result, 0)

    @patch("builtins.input", side_effect=[""])
    def test_salary_sacrifice_default_no(self, mock_input):
        """Empty input returns 0 (defaults to no)."""
        result = prompt_salary_sacrifice()
        self.assertEqual(result, 0)

    @patch("builtins.input", side_effect=["y", "5000"])
    def test_salary_sacrifice_yes_with_amount(self, mock_input):
        """Entering 'y' then a monthly amount; result is annual (×12)."""
        result = prompt_salary_sacrifice()
        self.assertEqual(result, 60000)  # 5000 × 12

    @patch("builtins.input", side_effect=["y", "abc", "3000"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_salary_sacrifice_retry_on_invalid(self, mock_stdout, mock_input):
        """Entering non-numeric amount retries and accepts valid input."""
        result = prompt_salary_sacrifice()
        self.assertEqual(result, 36000)  # 3000 × 12
        self.assertIn("Error: Please enter a whole number", mock_stdout.getvalue())

    @patch("builtins.input", side_effect=["yes"])
    def test_salary_sacrifice_not_strict_y(self, mock_input):
        """'yes' is not 'y', so it returns 0 (only bare 'y' counts)."""
        result = prompt_salary_sacrifice()
        self.assertEqual(result, 0)

    @patch("builtins.input", side_effect=["y", "4350"])
    def test_salary_sacrifice_partial_year(self, mock_input):
        """Partial-year contract: monthly sacrifice × contract months, not 12."""
        result = prompt_salary_sacrifice(start_month=8)
        self.assertEqual(result, 34800)  # 4350 × 8, not 4350 × 12


if __name__ == "__main__":
    unittest.main()
