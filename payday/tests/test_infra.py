import unittest
import pathlib
import tomllib


class TestInfra(unittest.TestCase):
    def test_pyproject_toml_exists(self):
        path = pathlib.Path("pyproject.toml")
        self.assertTrue(path.exists(), "pyproject.toml does not exist")

    def test_pyproject_toml_valid(self):
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)

        self.assertIn("project", data)
        self.assertEqual(data["project"].get("requires-python"), ">=3.10")


if __name__ == "__main__":
    unittest.main()
