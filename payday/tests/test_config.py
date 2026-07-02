import unittest
import json
import os
import tempfile
from payday.config import load_config, generate_template


class TestLoadConfig(unittest.TestCase):
    def test_missing_file_returns_none(self):
        result = load_config("/tmp/nonexistent_payday_test.json")
        self.assertIsNone(result)

    def test_valid_config_loads_all_fields(self):
        data = {
            "mode": "paye",
            "salary": 50000,
            "day_rate": None,
            "start_month": None,
            "existing_income": None,
            "existing_dividends": None,
            "days_off": 25,
            "working_days": None,
            "umbrella_margin": 25,
            "salary_sacrifice_enabled": False,
            "monthly_salary_sacrifice": None,
            "salary_sacrifice_cap": 100000,
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            self.assertEqual(result["mode"], "paye")
            self.assertEqual(result["salary"], 50000)
            self.assertEqual(result["days_off"], 25)
            self.assertFalse(result["salary_sacrifice_enabled"])
            self.assertIsNone(result["monthly_salary_sacrifice"])
        finally:
            os.unlink(path)

    def test_partial_config_absent_fields_are_none(self):
        data = {"mode": "inside_ir35", "day_rate": 600}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            self.assertEqual(result["mode"], "inside_ir35")
            self.assertEqual(result["day_rate"], 600)
            self.assertIsNone(result["salary"])
            self.assertIsNone(result["start_month"])
            self.assertIsNone(result["working_days"])
            self.assertIsNone(result["umbrella_margin"])
            self.assertIsNone(result["salary_sacrifice_cap"])
        finally:
            os.unlink(path)

    def test_malformed_json_raises_value_error(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{invalid json}")
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_invalid_mode_string_raises_value_error(self):
        data = {"mode": "invalid_mode"}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_mode_as_int(self):
        data = {"mode": 2}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            self.assertEqual(result["mode"], 2)
        finally:
            os.unlink(path)

    def test_invalid_field_type_raises_value_error(self):
        data = {"mode": "paye", "salary": "not_a_number"}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_start_month_out_of_range(self):
        data = {"mode": "paye", "start_month": 13}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_monthly_sacrifice_invalid_keyword(self):
        data = {"mode": "paye", "monthly_salary_sacrifice": "invalid"}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_monthly_sacrifice_valid_keywords(self):
        for kw in ("max", "auto"):
            data = {"mode": "paye", "monthly_salary_sacrifice": kw}
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                json.dump(data, f)
                path = f.name
            try:
                result = load_config(path)
                self.assertEqual(result["monthly_salary_sacrifice"], kw)
            finally:
                os.unlink(path)

    def test_salary_cap_none_when_not_present(self):
        data = {"mode": "paye", "salary_sacrifice_enabled": True}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            self.assertIsNone(result["salary_sacrifice_cap"])
        finally:
            os.unlink(path)


class TestGenerateTemplate(unittest.TestCase):
    def test_generates_valid_json_file(self):
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False
        ) as f:
            path = f.name
        try:
            generate_template(path)
            with open(path) as f:
                data = json.load(f)
            self.assertIn("mode", data)
            self.assertIn("salary", data)
            self.assertIn("day_rate", data)
            self.assertIn("monthly_salary_sacrifice", data)
            self.assertIsNone(data["salary"])
            self.assertIsNone(data["day_rate"])
        finally:
            os.unlink(path)




class TestMainModule(unittest.TestCase):
    def test_parse_args_no_args(self):
        from payday.__main__ import parse_args
        args = parse_args([])
        self.assertIsNone(args.config)

    def test_parse_args_config(self):
        from payday.__main__ import parse_args
        args = parse_args(["--config", "myconfig.json"])
        self.assertEqual(args.config, "myconfig.json")

    def test_parse_args_init_default(self):
        from payday.__main__ import parse_args
        args = parse_args(["--init"])
        self.assertEqual(args.init, "payday.json")

    def test_parse_args_init_custom(self):
        from payday.__main__ import parse_args
        args = parse_args(["--init", "custom.json"])
        self.assertEqual(args.init, "custom.json")

    def test_parse_args_init_lock(self):
        from payday.__main__ import parse_args
        args = parse_args(["--init", "--config", "c.json"])
        self.assertEqual(args.init, "payday.json")
        self.assertEqual(args.config, "c.json")


if __name__ == "__main__":
    unittest.main()
