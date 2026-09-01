import json
from pathlib import Path
from typing import Any


VALID_MODES = {"paye": 1, "inside_ir35": 2, "outside_ir35": 3}
VALID_SACRIFICE_KEYWORDS = {"max", "auto"}
VALID_REGIONS = {"scotland", "england", "wales", "northern_ireland", "rest_of_uk"}
VALID_STUDENT_LOAN_PLANS = {"plan1", "plan2", "plan4", "plan5"}
# Boolean fields accept both true and false as legitimate values.
BOOLEAN_FIELDS = {"salary_sacrifice_enabled", "is_paystream", "postgraduate_loan"}
# Fields where false is a sentinel meaning "off / no value".
FALSE_SENTINEL_FIELDS = {"income_target"}
FIELD_TYPES = {
    "mode": (str, int),
    "salary": (int, type(None)),
    "day_rate": (int, type(None)),
    "start_month": (int, bool, type(None)),
    "existing_income": (float, int, bool, type(None)),
    "existing_dividends": (float, int, bool, type(None)),
    "days_off": (int, bool, type(None)),
    "working_days": (int, bool, type(None)),
    "umbrella_margin": (int, bool, type(None)),
    "is_paystream": (bool, type(None)),
    "salary_sacrifice_enabled": (bool, type(None)),
    "monthly_salary_sacrifice": (int, str, bool, type(None)),
    "daily_salary_sacrifice": (int, str, bool, type(None)),
    "income_target": (int, bool, type(None)),
    "director_pension": (int, bool, type(None)),
    "region": (str, type(None)),
    "student_loan_plan": (str, type(None)),
    "postgraduate_loan": (bool, type(None)),
}
_ALL_FIELDS = [
    "mode",
    "salary",
    "day_rate",
    "start_month",
    "existing_income",
    "existing_dividends",
    "days_off",
    "working_days",
    "umbrella_margin",
    "is_paystream",
    "salary_sacrifice_enabled",
    "monthly_salary_sacrifice",
    "daily_salary_sacrifice",
    "income_target",
    "director_pension",
    "region",
    "student_loan_plan",
    "postgraduate_loan",
]


def _validate_field(key: str, value: Any) -> None:
    allowed = FIELD_TYPES[key]
    if isinstance(value, bool) and bool not in allowed:
        raise ValueError(f"'{key}': expected numeric type, got boolean")
    if isinstance(value, bool) and key not in BOOLEAN_FIELDS:
        if value is False:
            if key in FALSE_SENTINEL_FIELDS:
                return
            raise ValueError(f"'{key}': use 'true' for default, or 'null' to prompt")
        if key in ("salary", "day_rate", "mode"):
            raise ValueError(
                f"'{key}': true is not valid here — this field has no default"
            )
        return
    if not isinstance(value, allowed):
        raise ValueError(f"'{key}': expected {allowed}, got {type(value).__name__}")

    if key == "mode":
        if isinstance(value, str) and value not in VALID_MODES:
            raise ValueError(
                f"'mode': must be one of {', '.join(VALID_MODES)}, got '{value}'"
            )
        if isinstance(value, int) and value not in (1, 2, 3):
            raise ValueError(f"'mode': must be 1, 2, or 3, got {value}")

    elif key == "start_month" and value is not None:
        if not (1 <= value <= 12):
            raise ValueError(f"'start_month': must be 1-12 or null, got {value}")

    elif key in ("existing_income", "existing_dividends") and value is not None:
        if value < 0:
            raise ValueError(f"'{key}': must be >= 0, got {value}")

    elif key == "days_off" and value is not None:
        if value < 0:
            raise ValueError(f"'days_off': must be >= 0, got {value}")

    elif key == "working_days" and value is not None:
        if value < 1:
            raise ValueError(f"'working_days': must be >= 1, got {value}")

    elif key == "umbrella_margin" and value is not None:
        if value < 0:
            raise ValueError(f"'umbrella_margin': must be >= 0, got {value}")

    elif key in ("monthly_salary_sacrifice", "daily_salary_sacrifice") and isinstance(
        value, str
    ):
        if value not in VALID_SACRIFICE_KEYWORDS:
            raise ValueError(
                f"'{key}': string must be one of "
                f"{', '.join(sorted(VALID_SACRIFICE_KEYWORDS))}, got '{value}'"
            )

    elif key == "income_target" and value is not None:
        if value < 1:
            raise ValueError(f"'income_target': must be >= 1, got {value}")

    elif key == "director_pension" and isinstance(value, int):
        if value < 0:
            raise ValueError(f"'director_pension': must be >= 0, got {value}")

    elif key == "region" and value is not None:
        if value not in VALID_REGIONS:
            raise ValueError(
                f"'region': must be one of {', '.join(sorted(VALID_REGIONS))}, got '{value}'"
            )

    elif key == "student_loan_plan" and value is not None:
        if value not in VALID_STUDENT_LOAN_PLANS:
            raise ValueError(
                f"'student_loan_plan': must be one of "
                f"{', '.join(sorted(VALID_STUDENT_LOAN_PLANS))}, got '{value}'"
            )


def load_config(path: str) -> dict | None:
    filepath = Path(path)
    if not filepath.exists():
        return None

    try:
        raw = json.loads(filepath.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e

    if not isinstance(raw, dict):
        raise ValueError(f"Config must be a JSON object, got {type(raw).__name__}")

    config = {field: None for field in _ALL_FIELDS}

    for key in raw:
        if key not in FIELD_TYPES:
            raise ValueError(f"Unknown config key: '{key}'")
        _validate_field(key, raw[key])
        config[key] = raw[key]

    if (
        config.get("monthly_salary_sacrifice") is not None
        and config.get("daily_salary_sacrifice") is not None
    ):
        raise ValueError(
            "set either 'monthly_salary_sacrifice' or "
            "'daily_salary_sacrifice', not both"
        )

    return config


def generate_template(path: str) -> None:
    filepath = Path(path)
    template: dict[str, str | int | None] = {field: None for field in _ALL_FIELDS}
    template["mode"] = "paye"
    filepath.write_text(json.dumps(template, indent=2) + "\n")
    print(f"Template written to {filepath}")
