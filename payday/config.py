import json
from pathlib import Path


VALID_MODES = {"paye": 1, "inside_ir35": 2, "outside_ir35": 3}
VALID_SACRIFICE_KEYWORDS = {"max", "auto"}
FIELD_TYPES = {
    "mode": (str, int),
    "salary": (int, type(None)),
    "day_rate": (int, type(None)),
    "start_month": (int, type(None)),
    "existing_income": (float, int, type(None)),
    "existing_dividends": (float, int, type(None)),
    "days_off": (int, type(None)),
    "working_days": (int, type(None)),
    "umbrella_margin": (int, type(None)),
    "salary_sacrifice_enabled": (bool, type(None)),
    "monthly_salary_sacrifice": (int, str, type(None)),
    "salary_sacrifice_cap": (int, type(None)),
}
_ALL_FIELDS = [
    "mode", "salary", "day_rate", "start_month",
    "existing_income", "existing_dividends", "days_off",
    "working_days", "umbrella_margin", "salary_sacrifice_enabled",
    "monthly_salary_sacrifice", "salary_sacrifice_cap",
]



def _validate_field(key: str, value) -> None:
    allowed = FIELD_TYPES[key]
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

    elif key == "monthly_salary_sacrifice" and isinstance(value, str):
        if value not in VALID_SACRIFICE_KEYWORDS:
            raise ValueError(
                f"'monthly_salary_sacrifice': string must be one of "
                f"{', '.join(sorted(VALID_SACRIFICE_KEYWORDS))}, got '{value}'"
            )

    elif key == "salary_sacrifice_cap" and value is not None:
        if value < 1:
            raise ValueError(f"'salary_sacrifice_cap': must be >= 1, got {value}")


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

    return config


def generate_template(path: str) -> None:
    filepath = Path(path)
    template = {field: None for field in _ALL_FIELDS}
    template["mode"] = "paye"
    filepath.write_text(json.dumps(template, indent=2) + "\n")
    print(f"Template written to {filepath}")
