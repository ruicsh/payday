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

# Income Tax (Scotland — non-savings, non-dividend income)
# Source: https://www.gov.uk/scottish-income-tax
# PA and its £100k taper are UK-wide (same PERSONAL_ALLOWANCE / PA_TAPER_*).
SCOTTISH_STARTER_BAND_LIMIT: int = 16_537
SCOTTISH_BASIC_BAND_LIMIT: int = 29_526
SCOTTISH_INTERMEDIATE_BAND_LIMIT: int = 43_662
SCOTTISH_HIGHER_BAND_LIMIT: int = 75_000
SCOTTISH_ADVANCED_BAND_LIMIT: int = 125_140
SCOTTISH_STARTER_RATE: float = 0.19
SCOTTISH_BASIC_RATE: float = 0.20
SCOTTISH_INTERMEDIATE_RATE: float = 0.21
SCOTTISH_HIGHER_RATE: float = 0.42
SCOTTISH_ADVANCED_RATE: float = 0.45
SCOTTISH_TOP_RATE: float = 0.48

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

# Salary Sacrifice
MAX_SALARY_SACRIFICE: int = 60_000

# Student Loan repayment (2026/27)
# Source: https://www.gov.uk/repaying-your-student-loan/what-you-pay
STUDENT_LOAN_PLAN1_THRESHOLD: int = 26_900
STUDENT_LOAN_PLAN2_THRESHOLD: int = 29_385
STUDENT_LOAN_PLAN4_THRESHOLD: int = 33_795
STUDENT_LOAN_PLAN5_THRESHOLD: int = 25_000
STUDENT_LOAN_POSTGRADUATE_THRESHOLD: int = 21_000
STUDENT_LOAN_UNDERGRADUATE_RATE: float = 0.09
STUDENT_LOAN_POSTGRADUATE_RATE: float = 0.06

# National Insurance (Self-employed — Class 4)
# Source: https://www.gov.uk/self-employed-national-insurance-rates
# Source: https://www.gov.uk/government/publications/rates-and-allowances-national-insurance-contributions/rates-and-allowances-national-insurance-contributions
# Class 2 is treated as paid above the Small Profits Threshold (£7,105) since
# 6 Apr 2024 — no compulsory charge, so take-home only includes Class 4.
# Source: https://www.gov.uk/self-employed-national-insurance-rates
NI_CLASS4_LOWER_PROFITS_LIMIT: int = 12_570
NI_CLASS4_UPPER_PROFITS_LIMIT: int = 50_270
NI_CLASS4_SMALL_PROFITS_THRESHOLD: int = 7_105
NI_CLASS4_MAIN_RATE: float = 0.06
NI_CLASS4_UPPER_RATE: float = 0.02
NI_CLASS2_WEEKLY_RATE: float = (
    3.65  # voluntary only below SPT; not charged in take-home
)

# Employment Allowance (2026/27)
# Source: https://www.gov.uk/claim-employment-allowance
# Source: https://www.gov.uk/government/publications/employment-allowance-more-detailed-guidance
# Raised from £5,000 to £10,500 from April 2025; unchanged for 2026/27.
# Single-director companies (sole director as only employee) cannot claim:
# See https://www.gov.uk/government/publications/employment-allowance-more-detailed-guidance/single-director-companies-and-employment-allowance-further-employer-guidance
# and https://www.gov.uk/hmrc-internal-manuals/national-insurance-manual/nim06545
EMPLOYMENT_ALLOWANCE: int = 10_500

# PayStream salary-sacrifice administration charge (weekly, incl. 20% VAT)
# Source: PayStream "Salary Sacrifice — Contractor FAQs" (paystream-salary-sacrifice.pdf)
# £7.00 + 20% VAT = £8.40/week; charged only when sacrificing through PayStream.
PAYSTREAM_ADMIN_CHARGE_WEEKLY: float = 8.40
