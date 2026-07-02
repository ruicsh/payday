# Payday — UK Salary Calculator (2026/27)

A command-line tool to calculate take-home pay under three different UK employment structures, using 2026/27 tax rates.

Run it via `make run` (defaults to `payday.json`) or `make run myconfig.json`. Or directly with `python3 -m payday`.

---

## Modes

### 1. PAYE (Regular Employment)

For permanent employees on a fixed annual salary.

| Input | Default | Description |
|-------|---------|-------------|
| Annual gross salary | — | Your full-year salary before deductions |
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

| Input | Default | Description |
|-------|---------|-------------|
| Day rate | — | Daily contract rate |
| Working days/year | auto (252 − days‑off) | Days you work per year; auto‑computed from weekdays minus 9 E&W bank holidays, then subtracting days‑off (default 25 → ~227) |
| Umbrella weekly margin | £25 | Weekly umbrella company fee |
| Start month | None | Month contract starts (1–12) for mid-year proration |
| Existing employment income | £0 | Income already earned this tax year |
| Existing dividend income | £0 | Dividends already received this tax year |
| Salary sacrifice (monthly) | auto-calc | Reduces taxable income (capped at £60k/yr); auto-calc targets £100k ANI |

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

### 3. Outside IR35 (Limited Company)

For contractors operating through their own limited company. The company receives revenue, pays Corporation Tax, and distributes the remaining profit as dividends.

| Input | Default | Description |
|-------|---------|-------------|
| Day rate | — | Daily contract rate |
| Working days/year | auto (252 − days‑off) | Days you work per year; auto‑computed from weekdays minus 9 E&W bank holidays, then subtracting days‑off (default 25 → ~227) |
| Existing employment income | £0 | Income already earned this tax year (consumes PA and rate bands) |
| Director pension contribution | £0 | Annual company pension contribution to director's SIPP (≥ 0, max £60k); reduces Corporation Tax |

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
make run              # uses payday.json
make run custom.json  # uses custom.json
```

Or directly:

```bash
python3 -m payday --config payday.json
```

Follow the prompts to select a mode and enter your details. You'll be asked about salary sacrifice and existing income/dividends where applicable.

Salary sacrifice is capped at £60,000 per year. For help choosing how much to sacrifice, see `payday/calculators/optimal_sacrifice.py`.

---

## Configuration

Pre-fill prompts by passing a JSON config file with the `--config` flag. Configured values skip interactive input; absent fields default to null and prompt normally.

```bash
python3 -m payday --config myconfig.json
```

Generate a template to get started:

```bash
python3 -m payday --init              # writes payday.json
python3 -m payday --init custom.json  # writes custom.json
```

### Schema

All fields are optional. `null` or absent = prompt interactively (or use default).

| Field | Type | Accepts |
|-------|------|---------|
| `mode` | string or int | `"paye"` / `"inside_ir35"` / `"outside_ir35"` or `1` / `2` / `3` |
| `salary` | int or null | Annual gross salary (PAYE only) |
| `day_rate` | int or null | Daily contract rate (IR35 only) |
| `start_month` | int or null | 1–12, or null for full tax year |
| `existing_income` | float, int, or null | Income already earned this tax year (≥ 0) |
| `existing_dividends` | float, int, or null | Dividends already received (≥ 0) |
| `days_off` | int or null | Non-working days (≥ 0) |
| `working_days` | int or null | Net working days (≥ 1); if absent, auto-computed from days_off |
| `umbrella_margin` | int or null | Weekly umbrella fee (≥ 0, IR35 only) |
| `salary_sacrifice_enabled` | bool or null | Enable salary sacrifice |
| `monthly_salary_sacrifice` | int or str or null | Monthly amount, `"max"`, or `"auto"` |
| `income_target` | int, bool, or null | Target taxable income cap (≥ 1). `null` or `true` prompts you interactively. |
| `director_pension` | int, bool, or null | Annual company pension contribution to director's SIPP (≥ 0, max £60k). `true` = use £0 default. |

### Example

```json
{
  "mode": "inside_ir35",
  "day_rate": 600,
  "start_month": 4,
  "existing_income": 10000,
  "existing_dividends": 5000,
  "days_off": 25,
  "umbrella_margin": 25,
  "salary_sacrifice_enabled": true,
  "monthly_salary_sacrifice": 2000
}
```

> Config must be explicitly passed via `--config`. There is no auto-detection of `payday.json` in the working directory — this avoids surprise behaviour when switching directories.

---

## Testing

```bash
make test
```

Or directly:

```bash
python3 -m unittest discover -v -s payday/tests
```

All tests pass (347 test cases and counting).

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
