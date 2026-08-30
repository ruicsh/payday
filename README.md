# Payday — UK Salary Calculator (2026/27)

A command-line tool to calculate take-home pay under three different UK employment structures, using 2026/27 tax rates.

Run it via `make run` (defaults to `payday.json`) or `make run myconfig.json`. Or directly with `python3 -m payday`.

---

## Modes

### 1. PAYE (Regular Employment)

For permanent employees on a fixed annual salary.

| Input                      | Default   | Description                                                             |
| -------------------------- | --------- | ----------------------------------------------------------------------- |
| Annual gross salary        | —         | Your full-year salary before deductions                                 |
| Salary sacrifice (monthly) | auto-calc | Reduces taxable income (capped at £60k/yr); auto-calc targets £100k ANI |

**Flow:**

```
  Annual Gross Salary       £salary
    └─ Salary Sacrifice      -£N  (optional, monthly)
  ─────────────────────────────
  Adjusted Gross Salary     £N
    ├─ Personal Allowance   -£N
    ├─ Income Tax           -£N
    ├─ Employee NI (0/8/2%) -£N
    └─ Pension (5% EE)      -£N  (skipped if sacrifice)
  ─────────────────────────────
  Annual Take-Home          £N
  Monthly Take-Home         £N
```

### 2. Inside IR35 (Umbrella Company)

For contractors working through an umbrella company. The umbrella sits between the agency and the contractor, handling tax deductions.

| Input                      | Default               | Description                                                                                                                  |
| -------------------------- | --------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Day rate                   | —                     | Daily contract rate                                                                                                          |
| Working days/year          | auto (252 − days‑off) | Days you work per year; auto‑computed from weekdays minus 9 E&W bank holidays, then subtracting days‑off (default 25 → ~227) |
| Umbrella weekly margin     | £25                   | Weekly umbrella company fee                                                                                                  |
| Is your umbrella PayStream? | No                   | PayStream uses a net-pay salary-sacrifice model: the employer NI saving is passed back as additional gross pay, and a weekly admin charge (£7 + VAT) applies when sacrificing. Generic umbrellas reduce gross directly and retain the saving. |
| Start month                | None                  | Month contract starts (1–12) for mid-year proration                                                                          |
| Existing employment income | £0                    | Income already earned this tax year                                                                                          |
| Existing dividend income   | £0                    | Dividends already received this tax year                                                                                     |
| Salary sacrifice (monthly) | auto-calc             | Reduces taxable income (capped at £60k/yr); auto-calc targets £100k ANI. PayStream also supports a per-day sacrifice instead (see below). |

**Flow:**

```
  Assignment Rate         £day_rate × days
    ├─ Salary Sacrifice    -£N  (optional)
    ├─ Umbrella Margin     -£N
    ├─ Employer NI (15%)   -£N
    ├─ Apprenticeship Levy -£N
    └─ Employer Pension    -£N
  ────────────────────────────
  Gross Salary             £N
    ├─ Income Tax          -£N
    ├─ Employee NI (0/8/2%)-£N
    └─ Pension (5% EE)     -£N  (skipped if sacrifice)
  ────────────────────────────
  Annual Take-Home         £N
  20-Day Take-Home         £N
```

**PayStream (`is_paystream: true`):** salary sacrifice uses a net-pay pot — the sacrifice comes off the assignment before employer costs, so the employer NI saving is passed back to you and shown as an explicit `Employer NI saving (passed back)` line. A weekly admin charge of **£7.00 + 20% VAT (£8.40)** applies while sacrificing. PayStream also allows the sacrifice to be set as a fixed **per-day amount** (`daily_salary_sacrifice` in config, e.g. `"daily_salary_sacrifice": 50` → £50 × net working days); this is accepted only when `is_paystream` is true and cannot be combined with `monthly_salary_sacrifice`. A **generic umbrella** instead reduces gross directly by the sacrifice and retains the employer-cost saving.

### 3. Outside IR35 (Limited Company)

For contractors operating through their own limited company. The company receives revenue, pays Corporation Tax, and distributes the remaining profit as dividends.

| Input                         | Default               | Description                                                                                                                  |
| ----------------------------- | --------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Day rate                      | —                     | Daily contract rate                                                                                                          |
| Working days/year             | auto (252 − days‑off) | Days you work per year; auto‑computed from weekdays minus 9 E&W bank holidays, then subtracting days‑off (default 25 → ~227) |
| Existing employment income    | £0                    | Income already earned this tax year (consumes PA and rate bands)                                                             |
| Director pension contribution | £0                    | Annual company pension contribution to director's SIPP (≥ 0, max £60k); reduces Corporation Tax                              |

**Flow:**

```
  Company Revenue         £day_rate × days
    ├─ Director Salary    -£N
    ├─ Employer NI        -£N
    └─ Director Pension   -£N  (optional, reduces CT)
  ────────────────────────────
  Company Profit           £N
    └─ Corporation Tax     -£N  (19% / 25% with Marginal Relief)
  ────────────────────────────
  Distributable Profit     £N
    └─ Dividend Tax        -£N  (0% / 10.75% / 35.75% / 39.35%)
  ────────────────────────────
  Take-Home                £N
    (Salary £N | Dividends £N)
  20-Day Take-Home         £N
```

---

## Tax Rate References (2026/27)

All rates, thresholds and formulas used in this project are sourced from the following official HMRC / GOV.UK pages:

| Category                                         | Source                                                                                                                                                                                                                                                                                                           |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Income Tax (Personal Allowance, bands, rates)    | [https://www.gov.uk/income-tax-rates](https://www.gov.uk/income-tax-rates)                                                                                                                                                                                                                                       |
| Employee National Insurance (rates & thresholds) | [https://www.gov.uk/government/publications/rates-and-allowances-national-insurance-contributions/rates-and-allowances-national-insurance-contributions](https://www.gov.uk/government/publications/rates-and-allowances-national-insurance-contributions/rates-and-allowances-national-insurance-contributions) |
| Employer National Insurance (rates & thresholds) | [https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027](https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027)                                                                                                                                                       |
| Apprenticeship Levy (0.5%)                       | [https://www.gov.uk/guidance/pay-apprenticeship-levy](https://www.gov.uk/guidance/pay-apprenticeship-levy)                                                                                                                                                                                                       |
| Corporation Tax (rates & Marginal Relief)        | [https://www.gov.uk/corporation-tax-rates](https://www.gov.uk/corporation-tax-rates)                                                                                                                                                                                                                             |
| Dividend Tax (allowance & rates)                 | [https://www.gov.uk/tax-on-dividends](https://www.gov.uk/tax-on-dividends)                                                                                                                                                                                                                                       |
| IR35 / Off-Payroll Working Rules                 | [https://www.gov.uk/guidance/understanding-off-payroll-working-ir35](https://www.gov.uk/guidance/understanding-off-payroll-working-ir35)                                                                                                                                                                         |
| Umbrella Company Guidance                        | [https://www.gov.uk/guidance/working-through-an-umbrella-company](https://www.gov.uk/guidance/working-through-an-umbrella-company)                                                                                                                                                                               |

---

## Usage

```bash
make run              # shows a picker, or uses payday.json if it exists
make run custom.json  # uses custom.json
```

Or directly:

```bash
python3 -m payday --config payday.json
```

Or via the launcher (uses the project venv):

```bash
./payday.sh            # opens the contract picker (bare `python3 -m payday`)
./payday.sh --config custom.json
./payday.sh --init     # writes a payday.json template
```

When run without a valid `--config` (e.g. `make run` with no `payday.json` present), you'll be shown a list of contracts from `contracts/` and prompted to pick one. Selecting `[0] Manual entry` (or pressing Enter) skips the contract and prompts interactively.

Follow the prompts to select a mode and enter your details. You'll be asked about salary sacrifice and existing income/dividends where applicable.

Salary sacrifice is capped at £60,000 per year. For help choosing how much to sacrifice, see `payday/calculators/optimal_sacrifice.py`.

---

## Configuration

Pre-fill prompts by passing a JSON config file with the `--config` flag. Configured values skip interactive input; absent fields default to `null` and prompt normally.

```bash
python3 -m payday --config myconfig.json
```

Generate a template to get started:

```bash
python3 -m payday --init              # writes payday.json
python3 -m payday --init custom.json  # writes custom.json
```

### How config values behave

Every field follows a three-state convention:

| Value  | Meaning                                                                |
| ------ | ---------------------------------------------------------------------- |
| `null` / absent | Prompt interactively (or fall back to the field's default) |
| `true` | Use the field's default / auto value (see per-field notes below)       |
| `false` | Off / disabled — only valid for the fields that support it            |

`false` is only meaningful for `salary_sacrifice_enabled`, `is_paystream`, and `income_target`. Every other field rejects a JSON `false` (use `true` for the default, or `null` to prompt). `mode`, `salary`, and `day_rate` accept neither — they have no default and must be given a real value or prompted.

### Schema

All fields are optional.

| Field                      | Type                | Accepts                                                                                          |
| -------------------------- | ------------------- | ------------------------------------------------------------------------------------------------ |
| `mode`                     | string or int       | `"paye"` / `"inside_ir35"` / `"outside_ir35"` or `1` / `2` / `3`                                 |
| `salary`                   | int or null         | Annual gross salary (PAYE only)                                                                  |
| `day_rate`                 | int or null         | Daily contract rate (IR35 only)                                                                  |
| `start_month`              | int or null         | `1`–`12`, or `null`/`true` for full tax year                                                      |
| `existing_income`          | float, int, or null | Income already earned this tax year (≥ 0); `true` = £0                                           |
| `existing_dividends`       | float, int, or null | Dividends already received (≥ 0); `true` = £0                                                    |
| `days_off`                 | int or null         | Non-working days (≥ 0); `true` = default 25                                                      |
| `working_days`             | int or null         | Net working days (≥ 1); `true` or absent = auto-computed from `days_off`                         |
| `umbrella_margin`          | int or null         | Weekly umbrella fee (≥ 0, IR35 only); `true` = default £25                                       |
| `is_paystream`             | bool or null        | `true` = PayStream umbrella (net-pay salary sacrifice + £7+VAT weekly admin charge). `false` = generic umbrella (direct gross reduction). `null` prompts. |
| `salary_sacrifice_enabled` | bool or null        | `true` enables salary sacrifice. `false` *or* `null` skips sacrifice entirely — no prompt, £0.  |
| `monthly_salary_sacrifice` | int or str or null  | Monthly amount, `"max"`, or `"auto"` (`true` = `"auto"`). Mutually exclusive with `daily_*`.     |
| `daily_salary_sacrifice`   | int or str or null  | Per-day amount (PayStream only), `"max"`, or `"auto"` (`true` = `"auto"`). Mutually exclusive with `monthly_*`. |
| `income_target`            | int, bool, or null  | Fixed cap (≥ 1); `null`/`true` = prompt for cap (default £100,000); `false` = no target (max out pension). Only relevant with `"auto"` sacrifice. |
| `director_pension`         | int, bool, or null  | Annual company pension contribution to director's SIPP (≥ 0, max £60k). `true` = £0 (no contribution). |

### Examples

**PAYE — auto sacrifice targeting £100,000 ANI:**

```json
{
  "mode": "paye",
  "salary": 125000,
  "salary_sacrifice_enabled": true,
  "monthly_salary_sacrifice": "auto",
  "income_target": 100000
}
```

**Inside IR35 via PayStream — fixed per-day sacrifice:**

```json
{
  "mode": "inside_ir35",
  "day_rate": 750,
  "days_off": 5,
  "is_paystream": true,
  "salary_sacrifice_enabled": true,
  "daily_salary_sacrifice": 250
}
```

**Inside IR35 — max out the pension (no income target):**

```json
{
  "mode": "inside_ir35",
  "day_rate": 750,
  "is_paystream": true,
  "salary_sacrifice_enabled": true,
  "monthly_salary_sacrifice": "auto",
  "income_target": false
}
```

**Outside IR35 — mid-year start with a director pension:**

```json
{
  "mode": "outside_ir35",
  "day_rate": 800,
  "start_month": 10,
  "days_off": 20,
  "existing_income": 15000,
  "director_pension": 20000
}
```

### Gotchas

- **Sacrifice needs `salary_sacrifice_enabled: true`.** In config mode, a `null` or `false` value silently disables salary sacrifice (no prompt, £0). Only `true` runs the sacrifice logic.
- **`daily_salary_sacrifice` requires `is_paystream: true`** and is rejected for generic umbrellas. It also needs `working_days` (or `days_off`) to convert per-day to annual.
- **`monthly_*` and `daily_*` are mutually exclusive** — setting both fails validation.
- **`income_target: false` is not an error** — it deliberately means "no cap, maximise the pension". Every other field's `false` is rejected.
- `start_month`, `days_off`, `umbrella_margin`, `working_days`, `existing_*`, `director_pension`, and the sacrifice amounts all accept `true` as "use the default".

> `make run` passes `--config payday.json` by default, so a `payday.json` in the working directory is picked up automatically when using `make run`. Running bare `python3 -m payday` — or `./payday.sh` with no arguments, which forwards args verbatim — skips `payday.json` entirely and opens the contract picker instead.

---

## Testing

```bash
make test
```

Or directly:

```bash
python3 -m unittest discover -v -s payday/tests
```

All tests pass (393 test cases and counting).

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
