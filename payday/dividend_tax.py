from payday.constants import (
    PERSONAL_ALLOWANCE,
    DIVIDEND_ALLOWANCE,
    DIVIDEND_BASIC_RATE,
    DIVIDEND_HIGHER_RATE,
    DIVIDEND_ADDITIONAL_RATE,
    BASIC_RATE_BAND_LIMIT,
    HIGHER_RATE_BAND_LIMIT,
)
from payday.income_tax import calc_personal_allowance
from payday.models import DividendTaxResult

# Taxable income band limits (fixed, independent of Personal Allowance):
# Basic rate:  £0 to £37,700 of taxable income
# Higher rate: £37,701 to £125,140 of taxable income
# Additional:  above £125,140 of taxable income
_BASIC_BAND_WIDTH = BASIC_RATE_BAND_LIMIT - PERSONAL_ALLOWANCE  # 37,700
_HIGHER_BAND_WIDTH = HIGHER_RATE_BAND_LIMIT - BASIC_RATE_BAND_LIMIT  # 74,870


def calc_dividend_tax(dividends: int, salary: int) -> DividendTaxResult:
    """Tax on dividends, stacked on top of salary.
    Source: https://www.gov.uk/tax-on-dividends
    Source: https://www.gov.uk/income-tax-rates (band limits used for stacking)

    - £500 dividend allowance at 0% (separate from Personal Allowance)
    - Basic rate: 10.75% (taxable income £0–£37,700)
    - Higher rate: 35.75% (taxable income £37,701–£125,140)
    - Additional rate: 39.35% (taxable income above £125,140)
    - Personal Allowance consumed by salary first.
    - Total income = salary + dividends determines PA taper.

    >>> res = calc_dividend_tax(40000, 12570)
    >>> res.total_tax
    4821
    """
    total_income = salary + dividends
    pa, _ = calc_personal_allowance(total_income)

    # Taxable portion of salary after PA
    taxable_salary = max(0, salary - pa)

    # £500 dividend allowance at 0%, reduces basic rate band space
    dividend_allowance = min(dividends, DIVIDEND_ALLOWANCE)
    remaining_dividends = max(0, dividends - dividend_allowance)

    # --- Basic Rate Band (0 to 37,700 taxable income) ---
    basic_consumed_by_salary = min(taxable_salary, _BASIC_BAND_WIDTH)
    basic_band_remaining = _BASIC_BAND_WIDTH - basic_consumed_by_salary

    # Dividend allowance uses the bottom of the remaining basic band
    allowance_in_basic = min(dividend_allowance, basic_band_remaining)
    basic_for_taxable_dividends = basic_band_remaining - allowance_in_basic

    div_basic_band = min(remaining_dividends, basic_for_taxable_dividends)
    div_basic_tax = round(div_basic_band * DIVIDEND_BASIC_RATE)

    # --- Higher Rate Band (37,701 to 125,140 taxable income) ---
    remaining_after_basic = max(0, remaining_dividends - div_basic_band)

    higher_consumed_by_salary = max(
        0,
        min(taxable_salary, _BASIC_BAND_WIDTH + _HIGHER_BAND_WIDTH) - _BASIC_BAND_WIDTH,
    )
    higher_band_remaining = _HIGHER_BAND_WIDTH - higher_consumed_by_salary

    div_higher_band = min(remaining_after_basic, higher_band_remaining)
    div_higher_tax = round(div_higher_band * DIVIDEND_HIGHER_RATE)

    # --- Additional Rate Band (above 125,140 taxable income) ---
    div_additional_band = max(0, remaining_after_basic - div_higher_band)
    div_additional_tax = round(div_additional_band * DIVIDEND_ADDITIONAL_RATE)

    total_tax = div_basic_tax + div_higher_tax + div_additional_tax

    return DividendTaxResult(
        dividend_allowance=dividend_allowance,
        taxable_dividends=remaining_dividends,
        basic_band=div_basic_band,
        basic_tax=div_basic_tax,
        higher_band=div_higher_band,
        higher_tax=div_higher_tax,
        additional_band=div_additional_band,
        additional_tax=div_additional_tax,
        total_tax=total_tax,
    )
