# Implementation Plan: Config Mode Income Cap Prompt

## Overview

When running with `--config payday.json` and `monthly_salary_sacrifice: "auto"`, the user expects to be prompted for a "Taxable income cap" target when the config does not specify `salary_sacrifice_cap`. Currently, both `None` (not specified) and `True` (use default) silently fall back to £100,000 — the interactive prompt is only reached in the purely interactive (no-config) path.

The fix: in the config "auto" path, when `salary_sacrifice_cap` is `None` or `True`, fall back to the existing `prompt_int("Taxable income cap", ...)` prompt instead of silently using the default.

## Architecture Decisions

- **Minimal change**: Only modify the config path in `prompt_salary_sacrifice` (`cli.py:237-254`). The interactive prompt already exists at lines 271-275 and works correctly.
- **Consistent with config conventions**: `None` = "not specified, ask user", `True` = "use default, ask user" (matching how other config fields work — see `test_prompt_start_month_config_null_prompts`, etc.).
- **Reuse existing prompt code**: Call the same `prompt_int` that the interactive path uses, rather than duplicating logic.

## Task List

- [ ] Task 1: Modify the config "auto" path to prompt when `raw_cap` is `None`/`True`, and pass the user-specified cap to the optimal-sacrifice calculators
- [ ] Task 2: Update `test_prompt_salary_sacrifice_config_auto_with_cap_true` to expect interactive prompt behavior
- [ ] Task 3: Add tests for the `None` fallback (config without `salary_sacrifice_cap` should prompt)

## Files likely touched

- `payday/cli.py` (the fix)
- `payday/tests/test_cli.py` (test updates)

## Verification

- [ ] All existing tests pass
- [ ] New tests verify prompt fallback for both `None` and `True` cap values
- [ ] Manual smoke test with `--config payday.json` confirms prompt appears
