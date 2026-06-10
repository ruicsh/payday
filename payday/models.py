from dataclasses import dataclass
from typing import Dict, List, Optional


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
class StepLine:
    label: str
    amount: int
    indent: int = 0
    is_subtotal: bool = False


@dataclass
class SalaryBreakdown:
    mode: str
    inputs: Dict
    steps: List[StepLine]
    annual_take_home: int
    display_take_home: int
    income_tax: Optional[IncomeTaxResult] = None
    employee_ni: Optional[EmployeeNIResult] = None
    employer_ni: Optional[EmployerNIResult] = None
    corporation_tax: Optional[CorporationTaxResult] = None
    dividend_tax: Optional[DividendTaxResult] = None
