# Plan: `true` = use default, `null` = prompt

## Task 1 — Schema + validation
- `config.py`: add `bool` to `FIELD_TYPES` for all fields with defaults
- `config.py`: validate `True` is rejected for fields without defaults (`salary`, `day_rate`, `mode`)
- Tests: `True` accepted for each field with a default; `True` rejected for required-only fields

## Task 2 — `prompt_int` / `prompt_float`
- `cli.py`: `prompt_int` — `True` → use `default` param
- `cli.py`: `prompt_float` — same pattern
- Tests: `True` returns default; `null` prompts; explicit value works

## Task 3 — `prompt_start_month`, `prompt_existing_income`, `prompt_existing_dividends`
- `cli.py`: `True` → use default (full year / 0); `None` → prompt (breaking change)
- Tests: `True` uses default; `null` prompts; explicit value works

## Task 4 — `prompt_working_days`
- `cli.py`: `working_days: True` → auto-compute from available - days_off (default 25)
- `cli.py`: `days_off: True` → use default 25, auto-compute net
- Tests: `True` for each path; `null` prompts

## Task 5 — `prompt_salary_sacrifice`
- `cli.py`: `monthly_salary_sacrifice: True` → run optimal sacrifice calculation (auto)
- `cli.py`: `salary_sacrifice_cap: True` → use `default_cap` (100,000)
- Tests: `True` paths; `null` prompts
