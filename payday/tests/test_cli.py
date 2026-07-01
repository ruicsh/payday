import unittest
from unittest.mock import patch
from io import StringIO
from payday.cli import prompt_int, prompt_existing_income


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


if __name__ == "__main__":
    unittest.main()
