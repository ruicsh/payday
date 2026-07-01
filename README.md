# Payday — UK Salary Calculator (2026/27)

A command-line tool to calculate take-home pay under three different UK employment structures, using 2026/27 tax rates.

Run it via `make run` or `python3 -m payday`.

---

## Modes

### 1. PAYE (Regular Employment)

For permanent employees on a fixed annual salary.

- **Input:** annual gross salary, optional salary sacrifice (monthly)
- **Deductions:** Salary Sacrifice (if any), Income Tax (Personal Allowance £12,570, 20%/40%/45% bands), Employee NI (0%/8%/2%), Auto-enrolment Pension (5% on qualifying earnings — skipped when sacrifice is active)
- **Output:** annual and monthly take-home pay

### 2. Inside IR35 (Umbrella Company)

For contractors working through an umbrella company. The umbrella sits between the agency and the contractor, handling tax deductions.

- **Inputs:** day rate, working days per year, umbrella weekly margin, optional start month, optional existing income/dividends from this tax year, optional salary sacrifice (monthly)
- **Flow:** assignment rate → minus margin → minus Employer NI (15% above £5,000 Secondary Threshold) → minus Apprenticeship Levy (0.5%) → minus Employer Pension (3% on qualifying earnings) → gross salary → minus Salary Sacrifice → minus Income Tax → minus Employee NI → minus Employee Pension
- **Output:** annual and 20-day take-home pay (a common comparison metric for contractors)

### 3. Outside IR35 (Limited Company)

For contractors operating through their own limited company. The company receives revenue, pays Corporation Tax, and distributes the remaining profit as dividends.

- **Inputs:** day rate, working days per year, optional existing income from this tax year
- **Flow:** company revenue → minus director salary (£12,570) → minus Employer NI (15%) → minus Corporation Tax (19% small profits / 25% main rate with Marginal Relief) → distributable profit → minus Dividend Tax (10.75%/35.75%/39.35% with £500 allowance)
- **Output:** annual and 20-day take-home pay

---

## Usage

```bash
make run
```

Or directly:

```bash
python3 -m payday
```

Follow the prompts to select a mode and enter your details. You'll be asked about salary sacrifice and existing income/dividends where applicable.

For help choosing how much to sacrifice to avoid the Personal Allowance taper above £100k, see `payday/calculators/optimal_sacrifice.py`.

---

## Testing

```bash
make test
```

Or directly:

```bash
python3 -m unittest discover -v -s payday/tests
```

All tests pass (199 test cases and counting).

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

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
