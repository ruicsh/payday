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
            "income_target": 100000,
            "director_pension": None,
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
            self.assertIsNone(result["director_pension"])
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
            self.assertIsNone(result["income_target"])
            self.assertIsNone(result["director_pension"])
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
            self.assertIsNone(result["income_target"])
        finally:
            os.unlink(path)

    def test_bool_rejected_for_fields_without_defaults(self):
        """JSON true should be rejected for fields that have no default value."""
        for field in ("salary", "day_rate", "mode"):
            data = {} if field == "mode" else {"mode": "paye", field: True}
            if field == "mode":
                data = {"mode": True}
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

    def test_true_accepted_for_fields_with_defaults(self):
        """JSON true (use default) is valid for fields that have a default."""
        fields_with_defaults = [
            "start_month", "existing_income", "existing_dividends",
            "days_off", "working_days", "umbrella_margin",
            "monthly_salary_sacrifice", "income_target",
            "director_pension",
        ]
        for field in fields_with_defaults:
            data = {"mode": "paye", field: True}
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                json.dump(data, f)
                path = f.name
            try:
                result = load_config(path)
                self.assertIs(
                    result[field], True,
                    f"{field}: expected True, got {result[field]}",
                )
            finally:
                os.unlink(path)

    def test_false_rejected_for_non_boolean_fields(self):
        """JSON false should be rejected for all fields except salary_sacrifice_enabled."""
        fields = [
            "start_month", "existing_income", "existing_dividends",
            "days_off", "working_days", "umbrella_margin",
            "monthly_salary_sacrifice", "income_target",
            "salary", "day_rate", "director_pension",
        ]
        for field in fields:
            data = {"mode": "paye", field: False}
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

    # ── director_pension config tests ───────────────────────────────────

    def test_director_pension_in_config(self):
        """director_pension set in config is loaded correctly."""
        data = {"mode": "outside_ir35", "director_pension": 20000}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            self.assertEqual(result["director_pension"], 20000)
        finally:
            os.unlink(path)

    def test_director_pension_true_uses_default(self):
        """director_pension: true is valid and returns True (use default)."""
        data = {"mode": "outside_ir35", "director_pension": True}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            self.assertIs(result["director_pension"], True)
        finally:
            os.unlink(path)

    def test_director_pension_null_is_valid(self):
        """director_pension: null sets it to None."""
        data = {"mode": "outside_ir35", "director_pension": None}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            self.assertIsNone(result["director_pension"])
        finally:
            os.unlink(path)

    def test_director_pension_negative_rejected(self):
        """director_pension: -1 is rejected."""
        data = {"mode": "outside_ir35", "director_pension": -1}
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

    def test_director_pension_string_rejected(self):
        """director_pension: 'bad' is rejected."""
        data = {"mode": "outside_ir35", "director_pension": "bad"}
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

    def test_true_accepted_for_director_pension(self):
        """director_pension: true is accepted (disabling prompt with default)."""
        data = {"mode": "outside_ir35", "director_pension": True}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            self.assertIs(result["director_pension"], True)
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
