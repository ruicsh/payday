# Implementation Plan: Outside IR35 Director Pension Contributions

## Overview

Add support for company-to-director pension contributions in the Outside IR35 (Limited Company) calculation path. When operating Outside IR35, the company can make pension contributions directly to the director's SIPP — up to £60,000/year — before Corporation Tax is calculated. This reduces taxable profit and therefore Corporation Tax. The tool will prompt the user for the contribution amount and factor it into the waterfall breakdown.

**Current flow:**
```
Revenue → Director Salary (-£12,570) → Employer NI → Profit → CT → Dividends → Dividend Tax → Take-Home
```

**New flow:**
```
Revenue → Director Salary (-£12,570) → Employer NI → Director Pension (-£X) → Profit → CT → Dividends → Dividend Tax → Take-Home
```

## Architecture Decisions

- **Reuse existing constant**: The £60,000 annual allowance is the same as `MAX_SALARY_SACRIFICE` — reuse it directly.
- **Pension is NOT taxable income**: The contribution is a company expense, not personal income. It does not affect the director's income tax, NI, or dividend tax bands. Excluded from `year_taxable_income`.
- **Pension is NOT take-home**: The contribution goes into a pension pot. Take-home remains salary + net dividends.
- **Follow existing patterns**: Store value in `inputs` dict, display as deduction `StepLine` with `indent=1`, positioned between "Employer NI" and "Company Profit".
- **Prompt style**: Annual amount, consistent with how Outside IR35 handles figures annually.

## Dependency Graph

```
constants.py (MAX_SALARY_SACRIFICE — already exists)
    │
    ├── calculators/outside_ir35.py  (new director_pension param, profit recalculation)
    │
    ├── cli.py  (new prompt in run_once() mode 3, wire to calculator)
    │       │
    │       └── config.py  (new field: director_pension)
    │
    └── tests/
        ├── test_outside_ir35.py  (calculator unit tests with pension)
        ├── test_cli.py           (CLI prompt tests)
        └── test_config.py        (config field validation tests)
```

## Task List

### Phase 1: Foundation — Calculator

#### Task 1: Add `director_pension` to OutsideIR35Calculator

**Description:** Modify `OutsideIR35Calculator.calculate()` to accept a `director_pension: int = 0` parameter. Deduct it from profit before CT calculation. Add a "Director Pension" StepLine between "Employer NI (15%)" and "Company Profit". Store in `inputs` when > 0.

**Acceptance criteria:**
- [ ] `OutsideIR35Calculator.calculate(500, 240, director_pension=20000)` produces correct results
- [ ] Profit = revenue - salary - er_ni - director_pension
- [ ] CT calculated on reduced profit
- [ ] Waterfall shows "Director Pension" line as negative, indent=1
- [ ] NOT included in `year_taxable_income`
- [ ] Backward compatible: default `director_pension=0` identical to before

**Files:** `payday/calculators/outside_ir35.py`

### Phase 2: CLI

#### Task 2: Add CLI prompt for director pension

**Description:** In `run_once()` mode 3, add a prompt asking for the director pension contribution. Use `prompt_int()` with default 0, min 0, max `MAX_SALARY_SACRIFICE`. Pass to calculator.

**Files:** `payday/cli.py`

### Phase 3: Config

#### Task 3: Add `director_pension` to config system

**Description:** Add `director_pension` to `FIELD_TYPES`, `_ALL_FIELDS`, `_validate_field`, `generate_template`. Wire config value through `run_once()`.

**Files:** `payday/config.py`, `payday/cli.py`

### Checkpoint: Core Feature Complete

- [ ] All existing tests pass
- [ ] Outside IR35 with pension works end-to-end interactively and via config
- [ ] Backward compatible

### Phase 4: Tests

#### Task 4: Write comprehensive tests

**Description:** Calculator tests (various pension levels, profit/CT/take-home verification), CLI tests (prompt behavior, defaults, caps), config tests (validation).

**Files:** `payday/tests/test_outside_ir35.py`, `payday/tests/test_cli.py`, `payday/tests/test_config.py`

### Checkpoint: Complete

- [ ] All tests pass
- [ ] Lint passes
- [ ] Manual smoke test

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Different tax treatment for director pensions vs salary sacrifice | Low | Standard employer contribution, well-established |
| £60k AA could change | Low | In constants.py, easy to update |
| Existing configs without new field | Low | Default None → prompt, backward compatible |
