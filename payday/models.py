from dataclasses import dataclass


@dataclass
class IncomeTaxResult:
    personal_allowance: int
    tapered: bool
    taxable_income: int
    basic_band: int
    basic_tax: int
    higher_band: int
    higher_tax: int
    additional_band: int
    additional_tax: int
    total_tax: int
    # Scotland-specific bands (0 for rUK; populated when region == "scotland").
    # basic/higher are shared labels (Scot basic 20% == rUK basic 20%,
    # Scot higher 42% != rUK higher 40%). additional stays 0 for Scotland;
    # advanced/top replace it there.
    region: str = "rest_of_uk"
    starter_band: int = 0
    starter_tax: int = 0
    intermediate_band: int = 0
    intermediate_tax: int = 0
    advanced_band: int = 0
    advanced_tax: int = 0
    top_band: int = 0
    top_tax: int = 0


@dataclass
class EmployeeNIResult:
    below_pt: int
    main_band: int
    main_ni: int
    upper_band: int
    upper_ni: int
    total_ni: int


@dataclass
class EmployerNIResult:
    below_st: int
    above_st: int
    total_er_ni: int


@dataclass
class CorporationTaxResult:
    profit: int
    full_rate_tax: int
    marginal_relief: int
    total_ct: int


@dataclass
class DividendTaxResult:
    dividend_allowance: int
    taxable_dividends: int
    basic_band: int
    basic_tax: int
    higher_band: int
    higher_tax: int
    additional_band: int
    additional_tax: int
    total_tax: int


@dataclass
class PensionResult:
    eligible: bool
    qualifying_earnings: int
    employee_contribution: int
    employer_contribution: int


@dataclass
class StudentLoanResult:
    plan: str
    threshold: int
    rate: float
    income_above_threshold: int
    repayment: int


@dataclass
class Class4NIResult:
    below_lpl: int
    main_band: int
    main_ni: int
    upper_band: int
    upper_ni: int
    total_ni: int


@dataclass
class StepLine:
    label: str
    amount: int | float
    indent: int = 0
    is_subtotal: bool = False


@dataclass
class SalaryBreakdown:
    mode: str
    inputs: dict
    steps: list[StepLine]
    annual_take_home: int
    display_take_home: int
    year_taxable_income: int | None = None
    income_tax: IncomeTaxResult | None = None
    employee_ni: EmployeeNIResult | None = None
    employer_ni: EmployerNIResult | None = None
    corporation_tax: CorporationTaxResult | None = None
    dividend_tax: DividendTaxResult | None = None
    pension: PensionResult | None = None
    student_loan: StudentLoanResult | None = None
    postgraduate_loan: StudentLoanResult | None = None
    class4_ni: Class4NIResult | None = None
