# constants.py - UK Tax Bands and Rates for 2026/27

# Income Tax (England, Wales, NI)
PERSONAL_ALLOWANCE: int = 12_570
PA_TAPER_THRESHOLD: int = 100_000
PA_TAPER_RATE: float = 0.5  # £1 reduction per £2 over threshold
BASIC_RATE_BAND_LIMIT: int = 50_270  # end of basic rate band
HIGHER_RATE_BAND_LIMIT: int = 125_140  # end of higher rate band
BASIC_RATE: float = 0.20
HIGHER_RATE: float = 0.40
ADDITIONAL_RATE: float = 0.45

# National Insurance (Employee, Cat A)
NI_PRIMARY_THRESHOLD: int = 12_570
NI_UPPER_EARNINGS_LIMIT: int = 50_270
NI_MAIN_RATE: float = 0.08
NI_UPPER_RATE: float = 0.02

# National Insurance (Employer)
NI_SECONDARY_THRESHOLD: int = 5_000
NI_EMPLOYER_RATE: float = 0.15
APPRENTICESHIP_LEVY_RATE: float = 0.005

# Corporation Tax (Financial Year 2026)
CT_SMALL_PROFITS_RATE: float = 0.19
CT_MAIN_RATE: float = 0.25
CT_LOWER_LIMIT: int = 50_000
CT_UPPER_LIMIT: int = 250_000
CT_MARGINAL_RELIEF_FRACTION: float = 3 / 200

# Dividend Tax
DIVIDEND_ALLOWANCE: int = 500
DIVIDEND_BASIC_RATE: float = 0.1075
DIVIDEND_HIGHER_RATE: float = 0.3575
DIVIDEND_ADDITIONAL_RATE: float = 0.3935
