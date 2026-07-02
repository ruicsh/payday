import unittest
import pathlib
import tomllib
from payday.models import SalaryBreakdown


class TestInfra(unittest.TestCase):
    def test_pyproject_toml_exists(self):
        path = pathlib.Path("pyproject.toml")
        self.assertTrue(path.exists(), "pyproject.toml does not exist")

    def test_pyproject_toml_valid(self):
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)

        self.assertIn("project", data)
        self.assertEqual(data["project"].get("requires-python"), ">=3.10")

    def test_salary_breakdown_has_year_taxable_income(self):
        """SalaryBreakdown should accept year_taxable_income with default None."""
        b = SalaryBreakdown(mode="PAYE", inputs={}, steps=[], annual_take_home=0, display_take_home=0)
        self.assertIsNone(b.year_taxable_income)

        b2 = SalaryBreakdown(
            mode="PAYE", inputs={}, steps=[], annual_take_home=0, display_take_home=0,
            year_taxable_income=50000,
        )
        self.assertEqual(b2.year_taxable_income, 50000)


if __name__ == "__main__":
    unittest.main()
