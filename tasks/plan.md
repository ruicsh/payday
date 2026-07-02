# Implementation Plan: "max" Option for Salary Sacrifice

## Overview

Add a `max` keyword option to the salary sacrifice prompt so users can quickly set their sacrifice to the maximum allowed amount without manually calculating it. When the user types `max` at the monthly sacrifice prompt, the system auto-calculates the maximum annual sacrifice (capped by `MAX_SALARY_SACRIFICE` at £60,000 and by available income/budget).

## Architecture Decisions

- **Keyword**: The literal string `"max"` (case-insensitive) in the monthly amount prompt triggers max mode
- **Max calculation**:
  - PAYE: `min(salary, MAX_SALARY_SACRIFICE)`
  - Inside IR35: `min(annual_assignment - annual_margin, MAX_SALARY_SACRIFICE)`
  - Other modes: `0` (unaffected)
- **Monthly display**: The max is divided by contract months for monthly figure, same as manual entry
- **No changes** to `constants.py`, `optimal_sacrifice.py`, calculators, or formatters

## Dependency Graph

```
constants.py (MAX_SALARY_SACRIFICE = 60_000)  [NO CHANGE]
    │
    └── cli.py (prompt_salary_sacrifice)       [CHANGE: add "max" case]
            │
            └── tests/test_cli.py              [CHANGE: add "max" tests]
```

## Task List

### Task 1: Add "max" keyword handling to `prompt_salary_sacrifice()`

**Description:** Modify the `prompt_salary_sacrifice()` function in `cli.py` to accept `"max"` as a keyword in the monthly amount prompt. When entered, calculate the maximum allowed sacrifice and return it, with a confirmation message.

**Acceptance criteria:**
- [x] Typing `"max"` at the monthly prompt for PAYE mode sets sacrifice to `min(salary, 60000)`
- [x] Typing `"max"` at the monthly prompt for Inside IR35 mode sets sacrifice to `min(assignment - margin, 60000)`
- [x] `"MAX"`, `"Max"`, and `"max"` all work (case-insensitive)
- [x] Confirmation message displays: `"Maximum sacrifice: £{N}/yr (£{M}/mo)."`
- [x] Prompt text updated to show `[ENTER=auto, or 'max']` hint
- [x] `"max"` respects contract months (partial year) for the monthly display

**Verification:**
- [x] Tests pass: `python3 -m unittest payday.tests.test_cli -v`
- [x] Manual check: Run `python3 -m payday`, select PAYE mode, enter salary 150000, type `y` to sacrifice, type `max` → should show £60,000/yr (£5,000/mo)

**Dependencies:** None

**Files touched:**
- `payday/cli.py`

**Estimated scope:** Small (1 file, 1 function)

### Task 2: Add tests for "max" keyword

**Description:** Add unit tests for the new `"max"` keyword behavior in `test_cli.py`, covering PAYE and Inside IR35 modes, full and partial years, and edge cases.

**Acceptance criteria:**
- [x] Test: `"max"` on PAYE £150k salary → £60,000 annual sacrifice
- [x] Test: `"max"` on PAYE £30k salary → £30,000 annual sacrifice (gross below cap)
- [x] Test: `"max"` on Inside IR35 with enough budget → £60,000 or budget-limited
- [x] Test: `"max"` + partial year contract → annual amount correct, monthly = annual / months
- [x] Test: `"MAX"` works (case insensitive)
- [x] All existing CLI tests still pass (no regressions)

**Verification:**
- [x] `python3 -m unittest payday.tests.test_cli -v` passes (including new + existing tests)
- [x] `python3 -m unittest discover -s payday/tests -v` passes (full suite — 261 tests)

**Dependencies:** Task 1

**Files touched:**
- `payday/tests/test_cli.py`

**Estimated scope:** Small (1 file)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| "max" keyword accidentally triggers for a legitimate numeric entry | Low — numbers start with digits, not letters | Case-insensitive string match on `"max"` only |
| Inside IR35 max exceeds budget, causing `ValueError` | Medium | Clamp to `gross - annual_margin - 1` before applying `MAX_SALARY_SACRIFICE` |

## Summary

| Aspect | Detail |
|--------|--------|
| Files changed | 2 (`cli.py`, `test_cli.py`) |
| Total tasks | 2 |
| Estimated effort | ~30 minutes |
