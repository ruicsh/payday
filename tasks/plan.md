# Implementation Plan: Separate existing dividends from employment income

## Overview
`existing_income` is currently treated as employment income for PA consumption
and rate band usage — but users may include dividends in it, causing over-taxation.
The fix separates dividends so they count toward ANI (for PA tapering) without
consuming PAYE rate bands.

## Architecture Decision
`calc_income_tax` gains `existing_dividends: int = 0`. Employment-only income
(renamed mentally, not in the API) consumes PA and bands as before; dividends
feed only into `calc_adjusted_net_income` for PA tapering. The caller
(`InsideIR35Calculator.calculate`) accepts a new `existing_dividends` param
and passes it to both `calc_adjusted_net_income` (for tapering) and
`calc_income_tax` (for exclusion from band consumption).

## Task List

### Task 1: Add `existing_dividends` to `calc_income_tax`
- Accept `existing_dividends: int = 0`
- Use dividends in ANI for PA tapering (`calc_personal_allowance`)
- Do NOT use dividends for PA/rate band consumption in the marginal calculation
- Keep `existing_income` as employment-only consumption
- Update remaining_pa display

### Task 2: Add `existing_dividends` to `InsideIR35Calculator.calculate`
- Accept `existing_dividends: int = 0`
- Pass `employment_income=effective_gross + existing_income` to ANI
- Pass `dividend_income=existing_dividends` to ANI
- Pass `existing_dividends` to `calc_income_tax`
- Update all Inside IR35 callers (test files, CLI)

### Task 3: Update CLI prompts
- Add `prompt_existing_dividends()` for Inside IR35 mode
- Only prompt if partial year (same as existing_income behavior)
- Wire into `run_once()` for mode 2

## Dependencies
- Task 1 has no deps
- Task 2 depends on Task 1
- Task 3 depends on Task 2

## Risks
- The `existing_income` parameter already exists in the caller; existing tests
  pass `existing_income=0` or omit it — backward compat guaranteed by default.
- `calc_dividend_tax` also uses `existing_income` (in Outside IR35 path) but
  it has a separate concern; leaving it untouched for now.

## Verification
- Tests pass after each task
- Round-trip test updated for dividend scenarios
- Manual scenario: existing_income=16228, existing_dividends=15000 → PA=12570
