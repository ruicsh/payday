# Payday — UK Salary Calculator (2026/27)

A command-line tool to calculate take-home pay under four different UK employment structures, using 2026/27 tax rates.

Run it via `make run` (defaults to `payday.json`) or `make run myconfig.json`. Or directly with `python3 -m payday`.

---

## Modes

### 1. PAYE (Regular Employment)

For permanent employees on a fixed annual salary.

| Input                      | Default   | Description                                                                                                                             |
| -------------------------- | --------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Annual gross salary        | —         | Your full-year salary before deductions                                                                                                 |
| Other taxable income       | £0        | All other taxable income (savings interest, property, etc.); reduces remaining Personal Allowance/rate bands and feeds the Annual Allowance taper |
| Receives Child Benefit     | No        | Whether you (or your partner) receive Child Benefit — when `true` HICBC claws back Child Benefit at £60k–£80k ANI; auto-calc targets £60k ANI (saving ~47% for 1 child, ~56% for 3) instead of £100k |
| Number of children         | 1         | Number of children receiving Child Benefit (≥ 1); only used when Child Benefit is claimed — scales the annual benefit (£1,354 for 1, £2,251 for 2, £3,148 for 3) |
| Salary sacrifice (monthly) | auto-calc | Reduces taxable income (capped at £60k/yr, tapered to £10k when threshold >£200k and adjusted >£260k); auto-calc targets £100k ANI (or £60k when Child Benefit is claimed)    |
| Workplace pension scheme   | `relief_at_source` | `relief_at_source` (default — e.g. NEST: member pays 80% from net pay, provider claims 20% basic-rate relief and basic-rate band is extended by gross) or `net_pay` (contribution deducted before tax; relief at marginal rate). Only applies to auto-enrolment workplace pension; salary sacrifice is separate. |

**Flow:**

```
  Annual Gross Salary       £salary
    └─ Salary Sacrifice      -£N  (optional, monthly)
  ─────────────────────────────
  Adjusted Gross Salary     £N
    ├─ Personal Allowance   -£N
    ├─ Income Tax           -£N
    ├─ Employee NI (0/8/2%) -£N
    ├─ Pension (5% EE)      -£N  (80% net for relief_at_source, 100% for net_pay; skipped if sacrifice)
    ├─ Student Loan         -£N  (9% above plan threshold, optional)
    └─ Postgraduate Loan    -£N  (6% above £21k, stacks with Student Loan)
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
| Other taxable income       | £0                    | All other taxable income (savings interest, property, etc.); reduces remaining Personal Allowance/rate bands and feeds the Annual Allowance taper |
| Receives Child Benefit     | No                    | Whether you (or your partner) receive Child Benefit — when `true` HICBC claws back Child Benefit at £60k–£80k ANI; auto-calc targets £60k ANI instead of £100k |
| Number of children         | 1                     | Number of children receiving Child Benefit (≥ 1); only used when Child Benefit is claimed — scales the annual benefit (£1,354 for 1, £2,251 for 2, £3,148 for 3) |
| Salary sacrifice (monthly) | auto-calc             | Reduces taxable income (capped at £60k/yr, tapered to £10k when threshold >£200k and adjusted >£260k); auto-calc targets £100k ANI (or £60k when Child Benefit is claimed). PayStream also supports a per-day sacrifice instead (see below). |
| Workplace pension scheme   | `relief_at_source` | `relief_at_source` (default — e.g. NEST: member pays 80% from net pay, provider claims 20% and basic-rate band is extended) or `net_pay` (contribution deducted before tax; relief at marginal rate). Only applies to auto-enrolment workplace pension; salary sacrifice is separate. |

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
    ├─ Pension (5% EE)     -£N  (skipped if sacrifice)
    ├─ Student Loan        -£N  (9% above plan threshold, optional)
    └─ Postgraduate Loan   -£N  (6% above £21k, stacks with Student Loan)
  ────────────────────────────
  Annual Take-Home         £N
  20-Day Take-Home         £N
```

**PayStream (`is_paystream: true`):** salary sacrifice uses a net-pay pot — the sacrifice comes off the assignment before employer costs, so the employer NI saving is passed back to you and shown as an explicit `Employer NI saving (passed back)` line. A weekly admin charge of **£7.00 + 20% VAT (£8.40)** applies while sacrificing. PayStream also allows the sacrifice to be set as a fixed **per-day amount** (`daily_salary_sacrifice` in config, e.g. `"daily_salary_sacrifice": 50` → £50 × net working days); this is accepted only when `is_paystream` is true and cannot be combined with `monthly_salary_sacrifice`. A **generic umbrella** instead reduces gross directly by the sacrifice and retains the employer-cost saving.

### 3. Outside IR35 (Limited Company)

For contractors operating through their own limited company. The company receives revenue, pays Corporation Tax, and distributes the remaining profit as dividends.

| Input                         | Default               | Description                                                                                                             |
| ----------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Day rate                      | —                     | Daily contract rate                                                                                                     |
| Working days/year             | auto (252 − days‑off) | Days you work per year; auto‑computed from weekdays minus 9 E&W bank holidays, then subtracting days‑off (default 25 → ~227) |
| Existing employment income    | £0                    | Income already earned this tax year (consumes PA and rate bands)                                                        |
| Existing dividend income      | £0                    | Dividends already received this tax year (consumes PA and dividend rate bands)                                          |
| Other taxable income          | £0                    | All other taxable income (savings interest, property, etc.); consumes PA/rate bands and feeds the Annual Allowance taper |
| Director salary               | £12,570               | Annual director salary; above £12,570 incurs Income Tax + Employee NI (Scotland supported when `region: scotland`)      |
| Company expenses              | £0                    | Annual company running costs (accountancy, insurance, software, etc.); reduces Corporation Tax                          |
| Director pension contribution | £0                    | Annual company pension contribution to director's SIPP (≥ 0, max £60k, tapered to £10k when threshold >£200k and adjusted >£260k); reduces Corporation Tax |
| Retained profit               | £0                    | Profit retained in the company, not distributed; defers dividend tax (subject to CT)                                   |
| Employment Allowance          | No                    | Claim £10,500 Employment Allowance against Employer NI; single-director companies (sole director as only employee) cannot claim |
| VAT-registered                | No                    | Whether the company is VAT-registered (`vat_registered: true`); when not registered, `vat_scheme` is `none` (no VAT effect) |
| VAT scheme                    | `none`                | `standard` (cash-neutral) or `flat_rate` (keeps 20% VAT minus flat-rate % of VAT-inclusive turnover as taxable profit — see [VAT Flat Rate Scheme](https://www.gov.uk/vat-flat-rate-scheme) and [BIM31585](https://www.gov.uk/hmrc-internal-manuals/business-income-manual/bim31585)); only applies when `vat_registered: true` |
| Flat Rate VAT %               | 16.5%                 | Flat-rate % as decimal (e.g. `0.165` = 16.5% limited cost trader since 1 Apr 2017 per [VAT Notice 733 ¶4.4](https://www.gov.uk/guidance/flat-rate-scheme-for-small-businesses-vat-notice-733--2); sector rates 4%–14.5% otherwise); only applies when `vat_scheme: flat_rate` |
| Region                        | rUK                   | `scotland` for Scottish Income Tax on salary; rUK otherwise (dividends always UK-rate)                                 |

**Flow (Outside IR35 student loan is collected via Self Assessment on total income — salary + dividends):**

```
  Company Revenue         £day_rate × days
    ├─ Director Salary    -£N  (configurable, default £12,570)
    ├─ Employer NI        -£N
    │  └─ Employment Allowance  +£N  (opt-in, up to £10,500; see doc)
    ├─ Flat Rate VAT Surplus +£N  (when vat_registered+flat_rate: 20% VAT minus flat% of VAT-inclusive turnover; taxable per BIM31585)
    ├─ Company Expenses   -£N  (optional)
    └─ Director Pension   -£N  (optional, reduces CT)
  ────────────────────────────
  Company Profit           £N  (includes VAT surplus; subject to CT)
    └─ Corporation Tax     -£N  (19% / 25% with Marginal Relief)
  ────────────────────────────
  Distributable Profit     £N
    └─ Retained in Company -£N  (optional; defers dividend tax)
  ────────────────────────────
  Distributable Dividends  £N
    ├─ Income Tax (salary) -£N  (when salary > PA; Scotland supported)
    ├─ Employee NI (salary)-£N  (when salary > £12,570)
    ├─ Dividend Tax        -£N  (0% / 10.75% / 35.75% / 39.35%)
    ├─ Student Loan        -£N  (9% on salary+dividends above plan threshold, optional)
    └─ Postgraduate Loan   -£N  (6% on salary+dividends above £21k, stacks with Student Loan)
  ────────────────────────────
  Take-Home                £N
    (Salary £N | Dividends £N | Retained £N if any)
  20-Day Take-Home         £N
```

### 4. Sole Trader (Self-Employed)

For self-employed sole traders operating as an individual. The business receives turnover, deducts allowable expenses to arrive at trading profit, then pays Income Tax and Class 4 National Insurance via Self Assessment.

| Input                              | Default               | Description                                                                                                                  |
| ---------------------------------- | --------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Day rate                           | —                     | Daily contract rate                                                                                                          |
| Working days/year                  | auto (252 − days‑off) | Days you work per year; auto‑computed from weekdays minus 9 E&W bank holidays, then subtracting days‑off (default 25 → ~227) |
| Business expenses                  | £0                    | Annual allowable expenses deducted from turnover before profit                                                               |
| Personal pension contribution      | £0                    | Annual personal pension contribution (relief at source, ≥ 0, max £60k, tapered to £10k when threshold >£200k and adjusted >£260k); reduces Income Tax but not Class 4 NI |
| Existing employment income         | £0                    | Income already earned this tax year (consumes PA and rate bands)                                                             |
| Existing self-employment profit    | £0                    | Self-employment profit already earned this tax year (consumes PA, rate bands and Class 4 NI bands)                         |
| Other taxable income               | £0                    | All other taxable income (savings interest, property, etc.); consumes PA/rate bands and feeds the Annual Allowance taper    |
| First year as sole trader          | No                    | When `true` and the Self Assessment bill (Income Tax + Class 4 NI) exceeds £1,000, two 50% payments on account apply — cash needed is 200% of the bill ([GOV.UK](https://www.gov.uk/understand-self-assessment-bill/payments-on-account)) |

**Flow (Sole Trader — Self Assessment on trading profit; Class 2 treated as paid above £7,105, so only Class 4 is deducted):**

```
  Turnover              £day_rate × days
    └─ Business Expenses -£N  (allowable expenses)
  ────────────────────────────
  Trading Profit         £N
    └─ Personal Pension  -£N  (optional, max £60k; relief at source — reduces Income Tax, not Class 4 NI)
  ────────────────────────────
  Taxable Profit         £N
    ├─ Income Tax        -£N  (0% / 20% / 40% / 45%; Scotland 19%/20%/21%/42%/45%/48%)
    ├─ Class 4 NI        -£N  (0% / 6% / 2% via Self Assessment)
    ├─ Student Loan      -£N  (9% on taxable profit + existing income/self-employment above plan threshold, optional)
    └─ Postgraduate Loan -£N  (6% on taxable profit + existing income/self-employment above £21k, stacks with Student Loan)
  ────────────────────────────
  Annual Take-Home       £N
  20-Day Take-Home       £N
  Year Taxable Income    £N
  Cash Needed for Self Assessment  £N  (Income Tax + Class 4 NI; 200% when first year and bill > £1,000 due to two 50% payments on account)
  *Student loan and HICBC are collected via Self Assessment but excluded from the payments-on-account base.*
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
| Employment Allowance (£10,500, 2026/27)         | [https://www.gov.uk/claim-employment-allowance](https://www.gov.uk/claim-employment-allowance) · [https://www.gov.uk/government/publications/employment-allowance-more-detailed-guidance](https://www.gov.uk/government/publications/employment-allowance-more-detailed-guidance)                                                                                 |
| Employment Allowance (Single-Director Rule)      | [https://www.gov.uk/government/publications/employment-allowance-more-detailed-guidance/single-director-companies-and-employment-allowance-further-employer-guidance](https://www.gov.uk/government/publications/employment-allowance-more-detailed-guidance/single-director-companies-and-employment-allowance-further-employer-guidance) · [https://www.gov.uk/hmrc-internal-manuals/national-insurance-manual/nim06545](https://www.gov.uk/hmrc-internal-manuals/national-insurance-manual/nim06545) |
| VAT Flat Rate Scheme (FRS)                       | [https://www.gov.uk/vat-flat-rate-scheme](https://www.gov.uk/vat-flat-rate-scheme)                                                                                                                                                                                                                                     |
| VAT Flat Rate — How Much You Pay                 | [https://www.gov.uk/vat-flat-rate-scheme/how-much-you-pay](https://www.gov.uk/vat-flat-rate-scheme/how-much-you-pay)                                                                                                                                                                                                   |
| VAT Notice 733 (Flat Rate Scheme)                | [https://www.gov.uk/guidance/flat-rate-scheme-for-small-businesses-vat-notice-733--2](https://www.gov.uk/guidance/flat-rate-scheme-for-small-businesses-vat-notice-733--2)                                                                                                                                             |
| BIM31585 (Trading Profits — Flat Rate VAT)       | [https://www.gov.uk/hmrc-internal-manuals/business-income-manual/bim31585](https://www.gov.uk/hmrc-internal-manuals/business-income-manual/bim31585)                                                                                                                                                                   |
| Payments on Account (Self Assessment)          | [https://www.gov.uk/understand-self-assessment-bill/payments-on-account](https://www.gov.uk/understand-self-assessment-bill/payments-on-account)                                                                                                                                                                                |
| Limited Company Expenses                         | [https://www.gov.uk/limited-company-expenses](https://www.gov.uk/limited-company-expenses)                                                                                                                                                                                                                          |
| Student Loan Repayments (thresholds & rates)   | [https://www.gov.uk/repaying-your-student-loan/what-you-pay](https://www.gov.uk/repaying-your-student-loan/what-you-pay)                                                                                                                                                                                           |
| Self-Employed National Insurance (Class 4)     | [https://www.gov.uk/self-employed-national-insurance-rates](https://www.gov.uk/self-employed-national-insurance-rates)                                                                                                                                                                                             |
| Sole Trader / Self-Employment Setup            | [https://www.gov.uk/set-up-sole-trader](https://www.gov.uk/set-up-sole-trader)                                                                                                                                                                                                                                     |
| Allowable Business Expenses (Self-Employed)    | [https://www.gov.uk/expenses-if-youre-self-employed](https://www.gov.uk/expenses-if-youre-self-employed)                                                                                                                                                                                                           |
| Pension Tax Relief (Relief at Source)          | [https://www.gov.uk/tax-on-your-private-pension/pension-tax-relief](https://www.gov.uk/tax-on-your-private-pension/pension-tax-relief)                                                                                                                                                                           |
| Pension Annual Allowance                       | [https://www.gov.uk/tax-on-your-private-pension/annual-allowance](https://www.gov.uk/tax-on-your-private-pension/annual-allowance)                                                                                                                                                                               |
| Tapered Annual Allowance                       | [https://www.gov.uk/guidance/pension-schemes-work-out-your-tapered-annual-allowance](https://www.gov.uk/guidance/pension-schemes-work-out-your-tapered-annual-allowance)                                                                                                                                         |
| High Income Child Benefit Charge (HICBC)       | [https://www.gov.uk/child-benefit-tax-charge](https://www.gov.uk/child-benefit-tax-charge)                                                                                                                                                                                                                         |
| Child Benefit rates (2026/27)                  | [https://www.gov.uk/child-benefit-rates](https://www.gov.uk/child-benefit-rates)                                                                                                                                                                                                                                   |
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

Follow the prompts to select a mode and enter your details. You'll be asked about salary sacrifice, Child Benefit (for HICBC), existing income/dividends and other taxable income (savings, property, etc.) where applicable.

Salary sacrifice and all pension contributions are capped at the standard Annual Allowance of £60,000 per year, tapered to £10,000 when threshold income exceeds £200,000 and adjusted income exceeds £260,000 (see [Tapered Annual Allowance](https://www.gov.uk/guidance/pension-schemes-work-out-your-tapered-annual-allowance)). The waterfall shows `Annual Allowance (tapered to £N)` when the taper applies. For help choosing how much to sacrifice, see `payday/calculators/optimal_sacrifice.py` and `payday/annual_allowance.py`.

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

`false` is only meaningful for `salary_sacrifice_enabled`, `is_paystream`, `employment_allowance`, `has_child_benefit`, `postgraduate_loan`, `vat_registered`, and `income_target`. Every other field rejects a JSON `false` (use `true` for the default, or `null` to prompt). `mode`, `salary`, and `day_rate` accept neither — they have no default and must be given a real value or prompted.

### Schema

All fields are optional.

| Field                      | Type                | Accepts                                                                                          |
| -------------------------- | ------------------- | ------------------------------------------------------------------------------------------------ |
| `mode`                     | string or int       | `"paye"` / `"inside_ir35"` / `"outside_ir35"` / `"sole_trader"` or `1` / `2` / `3` / `4`         |
| `salary`                   | int or null         | Annual gross salary (PAYE only)                                                                  |
| `day_rate`                 | int or null         | Daily contract rate (IR35 / Sole Trader)                                                         |
| `start_month`              | int or null         | `1`–`12`, or `null`/`true` for full tax year                                                      |
| `existing_income`          | float, int, or null | Income already earned this tax year (≥ 0); `true` = £0                                           |
| `existing_dividends`       | float, int, or null | Dividends already received (≥ 0); `true` = £0                                                    |
| `existing_self_employment` | float, int, or null | Self-employment profit already earned (≥ 0, Sole Trader only); `true` = £0                      |
| `other_income`             | float, int, or null | All other taxable income (savings interest, property, etc., ≥ 0); `true` = £0. Feeds the Annual Allowance taper (`threshold >£200k` and `adjusted >£260k` → tapered to £10k) and reduces remaining Personal Allowance/rate bands |
| `days_off`                 | int or null         | Non-working days (≥ 0); `true` = default 25                                                      |
| `working_days`             | int or null         | Net working days (≥ 1); `true` or absent = auto-computed from `days_off`                         |
| `umbrella_margin`          | int or null         | Weekly umbrella fee (≥ 0, IR35 only); `true` = default £25                                       |
| `is_paystream`             | bool or null        | `true` = PayStream umbrella (net-pay salary sacrifice + £7+VAT weekly admin charge). `false` = generic umbrella (direct gross reduction). `null` prompts. |
| `salary_sacrifice_enabled` | bool or null        | `true` enables salary sacrifice. `false` *or* `null` skips sacrifice entirely — no prompt, £0.  |
| `monthly_salary_sacrifice` | int or str or null  | Monthly amount, `"max"`, or `"auto"` (`true` = `"auto"`). Mutually exclusive with `daily_*`. `"max"` is capped at the tapered Annual Allowance. |
| `daily_salary_sacrifice`   | int or str or null  | Per-day amount (PayStream only), `"max"`, or `"auto"` (`true` = `"auto"`). Mutually exclusive with `monthly_*`. `"max"` is capped at the tapered Annual Allowance. |
| `income_target`            | int, bool, or null  | Fixed cap (≥ 1); `null`/`true` = prompt for cap (default £100,000, or £60,000 when `has_child_benefit: true`); `false` = no target (max out pension, capped at tapered Annual Allowance). Only relevant with `"auto"` sacrifice. |
| `has_child_benefit`        | bool or null        | `true` = you (or your partner) receive Child Benefit — HICBC applies (£60k–£80k), auto-calc defaults to £60k ANI. `false`/`null` = no Child Benefit (default). |
| `num_children`             | int, bool, or null  | Number of children receiving Child Benefit (≥ 1); `true`/`null` = 1. Only used when `has_child_benefit: true`; scales the annual benefit (£1,354 for 1, £2,251 for 2, £3,148 for 3) and HICBC. |
| `director_salary`          | int, bool, or null  | Annual director salary (Outside IR35 only, ≥ 0); `true` = £12,570 (default optimal salary). Above £12,570 incurs Income Tax + Employee NI. |
| `director_pension`         | int, bool, or null  | Annual company pension contribution to director's SIPP (≥ 0, max £60k, tapered to £10k when threshold >£200k and adjusted >£260k). `true` = £0 (no contribution). |
| `company_expenses`         | int, bool, or null  | Annual company running costs (Outside IR35 only, ≥ 0); `true` = £0. Reduces Corporation Tax. |
| `retained_profit`          | int, bool, or null  | Profit retained in company (Outside IR35 only, ≥ 0); `true` = £0. Clamped to distributable profit; defers dividend tax. |
| `employment_allowance`     | bool or null        | `true` = Claim £10,500 Employment Allowance against Employer NI (Outside IR35 only). `false`/`null` = not claimed. Single-director companies (sole director as only employee) cannot claim. |
| `vat_registered`           | bool or null        | `true` = VAT-registered (Outside IR35 only). `false`/`null` = not registered (`vat_scheme: none`, no VAT effect). |
| `vat_scheme`               | string or null      | `standard` (cash-neutral) or `flat_rate` (keeps 20% VAT minus flat-rate % of VAT-inclusive turnover as taxable profit; see [VAT Flat Rate Scheme](https://www.gov.uk/vat-flat-rate-scheme) and [BIM31585](https://www.gov.uk/hmrc-internal-manuals/business-income-manual/bim31585)) or `none`. Only when `vat_registered: true`; otherwise `none`. |
| `vat_flat_rate`            | float or null       | Flat-rate % as decimal (e.g. `0.165` = 16.5% limited cost trader since 1 Apr 2017 per [VAT Notice 733 ¶4.4](https://www.gov.uk/guidance/flat-rate-scheme-for-small-businesses-vat-notice-733--2); sector rates 4%–14.5% otherwise). Only when `vat_scheme: flat_rate`; `true`/`null` = default 16.5%. |
| `business_expenses`        | int, bool, or null  | Annual allowable business expenses (Sole Trader only, ≥ 0); `true` = £0                          |
| `personal_pension`         | int, bool, or null  | Annual personal pension contribution (Sole Trader only, ≥ 0, max £60k, tapered to £10k when threshold >£200k and adjusted >£260k); `true` = £0. Reduces Income Tax but not Class 4 NI. |
| `is_first_year_sole_trader` | bool or null       | `true` = first year as sole trader — when the Self Assessment bill (Income Tax + Class 4 NI) exceeds £1,000, cash needed is 200% (bill + two 50% payments on account per [GOV.UK](https://www.gov.uk/understand-self-assessment-bill/payments-on-account)). `false`/`null` = not first year (cash = bill). Does not affect take-home. |
| `region`                   | string or null      | `"scotland"` for Scottish Income Tax; `"england"`/`"wales"`/`"northern_ireland"`/`"rest_of_uk"` (or `null`) = rUK rates. Non-Scottish aliases are equivalent to `rest_of_uk`. |
| `pension_method`           | string or null      | Workplace pension scheme for PAYE and Inside IR35 auto-enrolment: `"relief_at_source"` (default — e.g. NEST: 80% from net pay, 20% claimed by provider, basic-rate band extended) or `"net_pay"` (deducted before tax; relief at marginal rate). Only applies to auto-enrolment; salary sacrifice is separate. |
| `student_loan_plan`        | string or null      | Undergraduate plan: `"plan1"`, `"plan2"`, `"plan4"`, `"plan5"` (or `null` = no loan). All modes — PAYE/Inside IR35 via PAYE, Outside IR35 via Self Assessment on salary+dividends, Sole Trader via Self Assessment on taxable profit + existing. |
| `postgraduate_loan`        | bool or null        | `true` = Postgraduate Loan (6% above £21,000); stacks on top of `student_loan_plan`. `false`/`null` = none. Independent — valid without an undergraduate plan. |

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

**PAYE — Child Benefit, auto sacrifice targeting £60,000 ANI (HICBC):**

```json
{
  "mode": "paye",
  "salary": 75000,
  "salary_sacrifice_enabled": true,
  "monthly_salary_sacrifice": "auto",
  "has_child_benefit": true
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

**PAYE with Plan 2 + Postgraduate Loan (stacked):**

```json
{
  "mode": "paye",
  "salary": 50000,
  "student_loan_plan": "plan2",
  "postgraduate_loan": true
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

**Outside IR35 — full feature set (Scotland, custom salary, expenses, retained, allowance):**

```json
{
  "mode": "outside_ir35",
  "day_rate": 650,
  "days_off": 25,
  "region": "scotland",
  "director_salary": 9100,
  "company_expenses": 3000,
  "director_pension": 10000,
  "retained_profit": 15000,
  "employment_allowance": true
}
```

**Outside IR35 — zero retained with £5k expenses (rUK, default salary):**

```json
{
  "mode": "outside_ir35",
  "day_rate": 550,
  "company_expenses": 5000
}
```

**Outside IR35 — Flat Rate VAT (16.5% limited cost trader):**

```json
{
  "mode": "outside_ir35",
  "day_rate": 650,
  "vat_registered": true,
  "vat_scheme": "flat_rate",
  "vat_flat_rate": 0.165
}
```

**Sole Trader — with expenses, pension and existing self-employment:**

```json
{
  "mode": "sole_trader",
  "day_rate": 550,
  "days_off": 20,
  "business_expenses": 5000,
  "personal_pension": 10000,
  "existing_self_employment": 8000,
  "existing_income": 5000
}
```

### Gotchas

- **Sacrifice needs `salary_sacrifice_enabled: true`.** In config mode, a `null` or `false` value silently disables salary sacrifice (no prompt, £0). Only `true` runs the sacrifice logic.
- **`daily_salary_sacrifice` requires `is_paystream: true`** and is rejected for generic umbrellas. It also needs `working_days` (or `days_off`) to convert per-day to annual.
- **`monthly_*` and `daily_*` are mutually exclusive** — setting both fails validation.
- **`income_target: false` is not an error** — it deliberately means "no cap, maximise the pension". Every other field's `false` is rejected.
- `start_month`, `days_off`, `umbrella_margin`, `working_days`, `existing_*`, `director_salary`, `company_expenses`, `retained_profit`, `director_pension`, `business_expenses`, `personal_pension`, and the sacrifice amounts all accept `true` as "use the default".
- **Student loan collection differs by mode:** PAYE & Inside IR35 deduct via PAYE on gross salary; Outside IR35 collects via Self Assessment on total income (salary + dividends) — all post-CT dividends count, and the threshold is reduced by `existing_income` + `existing_dividends`; Sole Trader collects via Self Assessment on taxable profit + existing income/self-employment. For PAYE/Inside IR35 the loan is calculated on income **after** salary sacrifice.
- **Sole Trader pension vs expenses:** `personal_pension` reduces Income Tax (relief at source) but is **not** an allowable expense for Class 4 NI, which is charged on trading profit before pension. `business_expenses` reduce both.
- **Annual Allowance taper:** all pension inputs (`salary_sacrifice`, `director_pension`, `personal_pension`) are capped at the tapered Annual Allowance — £60k standard, reduced by £1 per £2 of adjusted income over £260k (when threshold income >£200k), floored at £10k. `other_income` (savings, property, etc.) counts towards `threshold`/`adjusted` income, so it can trigger the taper even when employment/self-employment income alone does not. The waterfall shows `Annual Allowance (tapered to £N)` when the taper applies.
- **Other taxable income:** `other_income` is prompted in every mode (default £0) and via config. It is *not* part of take-home from this employment/contract — it only reduces the remaining Personal Allowance/rate bands and feeds the Annual Allowance taper. Enter the total of all other taxable income for the year (savings interest, property, etc.).
- **Outside IR35 Employment Allowance:** single-director companies (sole director as only employee) **cannot** claim Employment Allowance. It requires at least one other employee/director paid above the £5,000 secondary threshold. Enable `employment_allowance: true` only if eligible — otherwise the HMRC claim will be rejected. The allowance reduces Employer NI by up to £10,500 (2026/27), covering the barest obligation but not eliminating the need for correct payroll reporting.
- **Outside IR35 director salary:** defaults to £12,570 (the Primary Threshold / Personal Allowance). Below £5,000 incurs no Employer NI; above £12,570 incurs Income Tax and Employee NI on the salary itself (Scottish rates apply when `region: scotland`). Dividends always use UK rates.
- **Outside IR35 retained profit:** clamped to distributable profit (CT still applies — only dividend tax is deferred). Retaining more than distributable simply results in zero dividends.
- **Outside IR35 company expenses:** treated as allowable company running costs (accountancy, insurance, software) reducing profit before Corporation Tax — distinct from Sole Trader `business_expenses`.
- **Outside IR35 VAT Flat Rate Scheme:** when `vat_registered: true` and `vat_scheme: flat_rate`, the surplus (20% VAT charged minus flat% of VAT-inclusive turnover) is **taxable trading income** added to Company Profit before Corporation Tax (per [BIM31585](https://www.gov.uk/hmrc-internal-manuals/business-income-manual/bim31585)). Shown as `Flat Rate VAT Surplus (X%)` in the waterfall. `standard` is cash-neutral (no profit effect). `vat_flat_rate` defaults to 16.5% (limited cost trader since 1 Apr 2017 per [VAT Notice 733 ¶4.4](https://www.gov.uk/guidance/flat-rate-scheme-for-small-businesses-vat-notice-733--2)); other sector rates 4%–14.5% can be set via `vat_flat_rate` (e.g. `0.145`).
- **High Income Child Benefit Charge (HICBC):** from £60,000 ANI Child Benefit is clawed back at 1% per *complete* £200 (≈£60k–£80k, rounded *down* per ITEPA s.681C), 100% wiped at £80,000. Set `has_child_benefit: true` to enable HICBC advisory (`Child Benefit (HICBC XX%…)`) and to make auto sacrifice target £60k (saving ~47% effective for 1 child, ~56% for 3). Set `num_children` to scale the benefit (£1,354/£2,251/£3,148 for 1/2/3). ANI = employment + other taxable income − salary sacrifice (PAYE/Inside) or + dividends/self-employment as applicable.

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

All tests pass (690 test cases and counting).

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
