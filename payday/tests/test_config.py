import unittest
import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            assert result is not None
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            assert result is not None
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json}")
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_invalid_mode_string_raises_value_error(self):
        data = {"mode": "invalid_mode"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_mode_as_int(self):
        data = {"mode": 2}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            assert result is not None
            self.assertEqual(result["mode"], 2)
        finally:
            os.unlink(path)

    def test_invalid_field_type_raises_value_error(self):
        data = {"mode": "paye", "salary": "not_a_number"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_start_month_out_of_range(self):
        data = {"mode": "paye", "start_month": 13}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_monthly_sacrifice_invalid_keyword(self):
        data = {"mode": "paye", "monthly_salary_sacrifice": "invalid"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
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
                assert result is not None
                self.assertEqual(result["monthly_salary_sacrifice"], kw)
            finally:
                os.unlink(path)

    def test_daily_sacrifice_int_accepted(self):
        data = {"mode": "inside_ir35", "daily_salary_sacrifice": 50}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            assert result is not None
            self.assertEqual(result["daily_salary_sacrifice"], 50)
        finally:
            os.unlink(path)

    def test_daily_sacrifice_valid_keywords(self):
        for kw in ("max", "auto"):
            data = {"mode": "inside_ir35", "daily_salary_sacrifice": kw}
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                json.dump(data, f)
                path = f.name
            try:
                result = load_config(path)
                assert result is not None
                self.assertEqual(result["daily_salary_sacrifice"], kw)
            finally:
                os.unlink(path)

    def test_daily_sacrifice_invalid_keyword(self):
        data = {"mode": "inside_ir35", "daily_salary_sacrifice": "invalid"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_both_monthly_and_daily_sacrifice_rejected(self):
        data = {
            "mode": "inside_ir35",
            "monthly_salary_sacrifice": 2000,
            "daily_salary_sacrifice": 50,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_salary_cap_none_when_not_present(self):
        data = {"mode": "paye", "salary_sacrifice_enabled": True}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            assert result is not None
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
            "start_month",
            "existing_income",
            "existing_dividends",
            "days_off",
            "working_days",
            "umbrella_margin",
            "is_paystream",
            "monthly_salary_sacrifice",
            "daily_salary_sacrifice",
            "income_target",
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
                assert result is not None
                self.assertIs(
                    result[field],
                    True,
                    f"{field}: expected True, got {result[field]}",
                )
            finally:
                os.unlink(path)

    def test_false_rejected_for_non_boolean_fields(self):
        """JSON false should be rejected for all fields except salary_sacrifice_enabled."""
        fields = [
            "start_month",
            "existing_income",
            "existing_dividends",
            "days_off",
            "working_days",
            "umbrella_margin",
            "monthly_salary_sacrifice",
            "daily_salary_sacrifice",
            "salary",
            "day_rate",
            "director_pension",
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

    def test_income_target_false_accepted(self):
        """income_target: false means 'no income target' (max pension)."""
        data = {"mode": "paye", "income_target": False}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            assert result is not None
            self.assertIs(result["income_target"], False)
        finally:
            os.unlink(path)

    def test_income_target_zero_rejected(self):
        """income_target: 0 is rejected (must be >= 1)."""
        data = {"mode": "paye", "income_target": 0}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            assert result is not None
            self.assertEqual(result["director_pension"], 20000)
        finally:
            os.unlink(path)

    def test_director_pension_true_uses_default(self):
        """director_pension: true is valid and returns True (use default)."""
        data = {"mode": "outside_ir35", "director_pension": True}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            assert result is not None
            self.assertIs(result["director_pension"], True)
        finally:
            os.unlink(path)

    def test_director_pension_null_is_valid(self):
        """director_pension: null sets it to None."""
        data = {"mode": "outside_ir35", "director_pension": None}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            assert result is not None
            self.assertIsNone(result["director_pension"])
        finally:
            os.unlink(path)

    def test_director_pension_negative_rejected(self):
        """director_pension: -1 is rejected."""
        data = {"mode": "outside_ir35", "director_pension": -1}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            assert result is not None
            self.assertIs(result["director_pension"], True)
        finally:
            os.unlink(path)

    # ── is_paystream config tests ─────────────────────────────────────

    def test_is_paystream_true_accepted(self):
        data = {"mode": "inside_ir35", "is_paystream": True}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            assert result is not None
            self.assertIs(result["is_paystream"], True)
        finally:
            os.unlink(path)

    def test_is_paystream_false_accepted(self):
        """false is a valid value (generic umbrella)."""
        data = {"mode": "inside_ir35", "is_paystream": False}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            assert result is not None
            self.assertIs(result["is_paystream"], False)
        finally:
            os.unlink(path)

    def test_is_paystream_null_accepted(self):
        data = {"mode": "inside_ir35", "is_paystream": None}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            assert result is not None
            self.assertIsNone(result["is_paystream"])
        finally:
            os.unlink(path)

    def test_is_paystream_string_rejected(self):
        data = {"mode": "inside_ir35", "is_paystream": "yes"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    # ── region config tests ────────────────────────────────────────────

    def test_region_scotland_accepted(self):
        for val in ("scotland", "england", "wales", "northern_ireland", "rest_of_uk"):
            data = {"mode": "paye", "region": val}
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(data, f)
                path = f.name
            try:
                result = load_config(path)
                assert result is not None
                self.assertEqual(result["region"], val)
            finally:
                os.unlink(path)

    def test_region_null_accepted(self):
        data = {"mode": "paye", "region": None}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            assert result is not None
            self.assertIsNone(result["region"])
        finally:
            os.unlink(path)

    def test_region_invalid_rejected(self):
        data = {"mode": "paye", "region": "france"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_region_absent_is_none(self):
        data = {"mode": "paye"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = load_config(path)
            assert result is not None
            self.assertIsNone(result["region"])
        finally:
            os.unlink(path)


class TestGenerateTemplate(unittest.TestCase):
    def test_generates_valid_json_file(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            generate_template(path)
            with open(path) as f:
                data = json.load(f)
            self.assertIn("mode", data)
            self.assertIn("salary", data)
            self.assertIn("day_rate", data)
            self.assertIn("monthly_salary_sacrifice", data)
            self.assertIn("daily_salary_sacrifice", data)
            self.assertIn("region", data)
            self.assertIsNone(data["salary"])
            self.assertIsNone(data["day_rate"])
            self.assertIsNone(data["region"])
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


class TestContractSelection(unittest.TestCase):
    def setUp(self):
        from payday import __main__

        self._orig_dir = __main__.CONTRACTS_DIR
        self._tmpdir = tempfile.mkdtemp()
        __main__.CONTRACTS_DIR = Path(self._tmpdir)

    def tearDown(self):
        from payday import __main__

        __main__.CONTRACTS_DIR = self._orig_dir
        shutil.rmtree(self._tmpdir)

    def _write_contract(self, name, data):
        path = os.path.join(self._tmpdir, name)
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def test_list_contracts_missing_dir(self):
        from payday import __main__

        __main__.CONTRACTS_DIR = Path("/nonexistent/contracts/dir")
        try:
            self.assertEqual(__main__.list_contracts(), [])
        finally:
            __main__.CONTRACTS_DIR = self._orig_dir

    def test_list_contracts_empty_dir(self):
        from payday.__main__ import list_contracts

        self.assertEqual(list_contracts(), [])

    def test_list_contracts_sorted(self):
        from payday.__main__ import list_contracts

        self._write_contract("zeta.json", {"mode": "paye"})
        self._write_contract("alpha.json", {"mode": "paye"})
        names = [p.name for p in list_contracts()]
        self.assertEqual(names, ["alpha.json", "zeta.json"])

    def test_select_contract_no_contracts(self):
        from payday.__main__ import select_contract

        self.assertIsNone(select_contract())

    def test_select_contract_manual_entry(self):
        from payday.__main__ import select_contract

        self._write_contract("alpha.json", {"mode": "paye"})
        with patch("builtins.input", return_value="0"):
            self.assertIsNone(select_contract())

    def test_select_contract_picks_contract(self):
        from payday.__main__ import select_contract

        self._write_contract("alpha.json", {"mode": "paye", "salary": 50000})
        with patch("builtins.input", return_value="1"):
            config = select_contract()
        self.assertIsNotNone(config)
        assert config is not None
        self.assertEqual(config["salary"], 50000)

    def test_select_contract_invalid_then_valid(self):
        from payday.__main__ import select_contract

        self._write_contract("alpha.json", {"mode": "paye", "salary": 50000})
        with patch("builtins.input", side_effect=["abc", "99", "1"]):
            config = select_contract()
        self.assertIsNotNone(config)
        assert config is not None
        self.assertEqual(config["salary"], 50000)


if __name__ == "__main__":
    unittest.main()
