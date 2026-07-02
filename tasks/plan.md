# Implementation Plan: `payday.json` Config File Support

## Overview

Allow users to pre-define answers to all CLI prompts in a `payday.json` file. When a value is present in the config, the corresponding prompt is skipped and the value is used automatically. When absent or `null`, the interactive prompt is shown as normal. Fully backward compatible — no config file means full interactive mode (unchanged behavior).

## Architecture Decisions

- **Flat JSON schema** — one level, field names map 1:1 to prompt parameters. Simpler than nested mode-specific sections.
- **Null = prompt interactively** — any field set to `null` or missing triggers the interactive prompt for that value.
- **Explicit transparency** — when a config value is used, print `"Using value from payday.json: X"` so the user knows what's happening.
- **Pass config as optional parameter** — `config: dict | None` flows from `main()` → `run_once()` → each prompt function. No module-level global state. Easy to test.
- **`argparse` for CLI flags** — stdlib-only, zero new dependencies. `--config PATH`, `--init [PATH]`.
- **`--no-config` flag** — force interactive mode even if `payday.json` exists in CWD. No auto-detection to avoid surprise.

## `payday.json` Schema

```json
{
  "mode": "paye",
  "salary": 100000,
  "day_rate": null,
  "start_month": null,
  "existing_income": null,
  "existing_dividends": null,
  "days_off": 25,
  "working_days": null,
  "umbrella_margin": 25,
  "salary_sacrifice_enabled": false,
  "monthly_salary_sacrifice": null,
  "salary_sacrifice_cap": 100000
}
```

## Task List

### Phase 1: Foundation

#### ✅ Task 1: Create `payday/config.py` — Config loader, validator, and template generator

**Description:** Create a new module that loads a `payday.json` file from disk, validates its schema, and generates a template. Uses only stdlib `json` and `pathlib`.

**Files touched:** `payday/config.py` (new), `payday/tests/test_config.py` (new)

**Status:** ✅ Complete

---

#### Task 2: Add CLI argument parsing and config plumbing to `__main__.py` and `main()`

**Description:** Add `argparse` to `__main__.py` to accept `--config PATH`, `--init [PATH]`, and `--no-config` flags. Load config and pass it through the call chain. Modify `main()` and `run_once()` signatures to accept an optional config dict.

**Acceptance criteria:**
- [ ] `python -m payday --config payday.json` loads and passes config
- [ ] `python -m payday --init` writes `./payday.json` template and exits
- [ ] `python -m payday --init custom.json` writes to custom path
- [ ] `python -m payday --no-config` forces interactive mode
- [ ] `python -m payday` (no args) works as before (no config, fully interactive)
- [ ] `python -m payday --config missing.json` shows clean error
- [ ] `main()` accepts `config: dict | None = None` parameter (backward compatible)
- [ ] `run_once()` accepts `config: dict | None = None` parameter (backward compatible)

**Files touched:** `payday/__main__.py`, `payday/cli.py`

---

### Checkpoint: Foundation
- [ ] `payday/config.py` loads and validates config files correctly
- [ ] `--config`, `--init`, `--no-config` flags all work
- [ ] Interactive mode still works (no regressions when no config)
- [ ] Existing 273 tests still pass

---

### Phase 2: Core Integration

#### Task 3: Integrate config into mode selection and all prompt functions

**Description:** Modify `select_mode()`, `prompt_int()`, `prompt_float()`, and all mode-specific prompt functions to accept a config dict and use its values to skip interactive prompting. When a value is used from config, print a confirmation message.

**Acceptance criteria:**
- [ ] `select_mode(config)` — if `config["mode"]` is set, print confirmation and return mode number
- [ ] `prompt_int(..., config_value=...)` — if value provided, skip prompt and return validated value
- [ ] `prompt_float(config_value=...)` — same behavior for floats
- [ ] All mode-specific prompts check config before prompting
- [ ] `prompt_salary_sacrifice` accepts config values
- [ ] Partial config works (some values from config, some prompted)
- [ ] Interactive mode unchanged when no config

**Files touched:** `payday/cli.py`

---

### Checkpoint: Core Integration
- [ ] Full PAYE mode works via `payday.json` with zero prompts
- [ ] Full Inside IR35 mode works via `payday.json` with zero prompts
- [ ] Full Outside IR35 mode works via `payday.json` with zero prompts
- [ ] Salary sacrifice (manual, auto, max) works via config
- [ ] Partial config works (some values from config, some prompted)
- [ ] Interactive mode unchanged when no `--config` flag

---

### Phase 3: Tests and Polish

#### Task 4: Add tests for config-aware prompts

**Description:** Add tests in `test_cli.py` that verify prompt functions auto-answer when config values are provided, and skip interactive input.

**Acceptance criteria:**
- [ ] Test: `select_mode({"mode": "paye"})` returns 1 without reading input
- [ ] Test: `prompt_int(config_value=42)` returns 42 without reading input
- [ ] Test: `prompt_salary_sacrifice(config values)` returns correct sacrifice without prompting
- [ ] Test: `run_once(config=full_paye_config)` runs without any user input
- [ ] All existing CLI tests still pass (no regressions)

**Files touched:** `payday/tests/test_cli.py`

---

### Checkpoint: Complete
- [ ] All acceptance criteria met
- [ ] Full test suite passes
- [ ] Backward compatible — no config = unchanged UX
- [ ] Ready for review

## Dependency Graph

```
NEW: payday/config.py          (JSON loader, schema validation, template generator)
       │
       ├── payday/__main__.py  (add argparse --config, --init, --no-config)
       │       │
       │       └── payday/cli.py:main()      (accept config param)
       │               │
       │               └── payday/cli.py:run_once()   (accept+pass config)
       │                       │
       │                       ├── select_mode()          (check config.mode)
       │                       ├── prompt_int/float()     (check config.field)
       │                       ├── prompt_start_month()   (check config.start_month)
       │                       ├── prompt_existing_income/dividends() (check config)
       │                       ├── prompt_working_days()  (check config)
       │                       └── prompt_salary_sacrifice() (check config)
       │
       └── payday/tests/test_config.py  (new: config loading, validation, template)
       └── payday/tests/test_cli.py     (mod: add config-aware tests)
```

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `prompt_float()` type checks break for `config_value` int → float | Low | `config_value` passed as-is; `prompt_float` returns `float(config_value)` if int |
| `"max"` keyword in `monthly_salary_sacrifice` JSON field conflicts with strict int validation | Low | Allow `int` / `"max"` / `"auto"` / `null` union type in schema validation |
| Interactive fallback confusing when some fields set, some not | Medium | Each auto-answered field prints a clear `"Using value from payday.json: X"` line |

## Summary

| Aspect | Detail |
|--------|--------|
| New files | 2 (`payday/config.py`, `payday/tests/test_config.py`) |
| Modified files | 3 (`payday/__main__.py`, `payday/cli.py`, `payday/tests/test_cli.py`) |
| Total tasks | 4 |
| Estimated effort | ~4-6 hours |
