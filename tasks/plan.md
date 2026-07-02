# Implementation Plan: Precise Working Days with UK Bank Holidays + Days-Off Prompt

## Overview
Replace the hard-coded `working_days: int` prompt default of 240 with a two-step flow: auto-compute exact working days from weekdays minus UK bank holidays, then ask the user how many days-off they want to take. Supports England & Wales, mid-year proration, and manual override.

## Task List

### Task 1: Holiday data + counting function
- New `payday/bank_holidays.py`
- `ENGLAND_WALES_2026_27: list[date]` with 8 entries (substitute-day aware)
- `weekdays_in_range(start, end) -> int`
- `working_days_in_range(start, end, holidays) -> int`

### Task 2: Tax-year helpers
- Extend `payday/tax_year.py`
- `tax_year_working_days() -> int` — full-year count (weekdays minus holidays)
- `contract_working_days(start_month, days_off) -> int` — pro-rate for mid-year

### Task 3: CLI prompt update
- Replace single-arg prompt with: show computed total, prompt for days-off (default 25), allow override
- Mid-year start shows prorated figure

### Task 4: Calculator wiring
- Wire `days_off` through Inside IR35 / Outside IR35 calculator calls
- Update defaults in calculators

### Task 5: Formatter + test updates
- Update test fixtures for new defaults (252 / 25 → 227)
- Keep a manual-override test at 240

### Task 6: Docs
- SPEC.md, README.md, REQUIREMENTS.md

## Dependencies
- Task 1 → 2 → 3 → 4 → 5 → 6

## Verification
- Tests pass after each task
- `python3 -m unittest discover -v -s payday/tests`
