# constants.py - UK Tax Bands and Rates for 2026/27

# Income Tax (England, Wales, NI)
# Source: https://www.gov.uk/income-tax-rates
PERSONAL_ALLOWANCE: int = 12_570
PA_TAPER_THRESHOLD: int = 100_000
PA_TAPER_RATE: float = 0.5  # £1 reduction per £2 over threshold
BASIC_RATE_BAND_LIMIT: int = 50_270  # end of basic rate band
HIGHER_RATE_BAND_LIMIT: int = 125_140  # end of higher rate band
BASIC_RATE: float = 0.20
HIGHER_RATE: float = 0.40
ADDITIONAL_RATE: float = 0.45

# National Insurance (Employee, Cat A)
# Source: https://www.gov.uk/government/publications/rates-and-allowances-national-insurance-contributions/rates-and-allowances-national-insurance-contributions
NI_PRIMARY_THRESHOLD: int = 12_570
NI_UPPER_EARNINGS_LIMIT: int = 50_270
NI_MAIN_RATE: float = 0.08
NI_UPPER_RATE: float = 0.02

# National Insurance (Employer)
# Source: https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027
NI_SECONDARY_THRESHOLD: int = 5_000
NI_EMPLOYER_RATE: float = 0.15
APPRENTICESHIP_LEVY_RATE: float = (
    0.005  # Source: https://www.gov.uk/guidance/pay-apprenticeship-levy
)

# Corporation Tax (Financial Year 2026)
# Source: https://www.gov.uk/corporation-tax-rates
CT_SMALL_PROFITS_RATE: float = 0.19
CT_MAIN_RATE: float = 0.25
CT_LOWER_LIMIT: int = 50_000
CT_UPPER_LIMIT: int = 250_000
CT_MARGINAL_RELIEF_FRACTION: float = 3 / 200

# Dividend Tax
# Source: https://www.gov.uk/tax-on-dividends
DIVIDEND_ALLOWANCE: int = 500
DIVIDEND_BASIC_RATE: float = 0.1075
DIVIDEND_HIGHER_RATE: float = 0.3575
DIVIDEND_ADDITIONAL_RATE: float = 0.3935

# Pension (Auto-Enrolment)
# Source: https://www.gov.uk/workplace-pensions/what-you-your-employer-and-the-government-pay
PENSION_TRIGGER: int = 10_000
PENSION_QUALIFYING_LOWER_LIMIT: int = 6_240
PENSION_QUALIFYING_UPPER_LIMIT: int = 50_270
PENSION_EMPLOYEE_RATE: float = 0.05
PENSION_EMPLOYER_RATE: float = 0.03
