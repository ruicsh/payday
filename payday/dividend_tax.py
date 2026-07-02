from payday.constants import (
    PERSONAL_ALLOWANCE,
    DIVIDEND_ALLOWANCE,
    DIVIDEND_BASIC_RATE,
    DIVIDEND_HIGHER_RATE,
    DIVIDEND_ADDITIONAL_RATE,
    BASIC_RATE_BAND_LIMIT,
    HIGHER_RATE_BAND_LIMIT,
)
from payday.income_tax import calc_adjusted_net_income, calc_personal_allowance
from payday.models import DividendTaxResult

# Taxable income band limits (fixed, independent of Personal Allowance):
# Basic rate:  £0 to £37,700 of taxable income
# Higher rate: £37,701 to £125,140 of taxable income
# Additional:  above £125,140 of taxable income
_BASIC_BAND_WIDTH = BASIC_RATE_BAND_LIMIT - PERSONAL_ALLOWANCE  # 37,700
_HIGHER_BAND_WIDTH = HIGHER_RATE_BAND_LIMIT - BASIC_RATE_BAND_LIMIT  # 74,870


def _compute_dividend_tax_bands(
    dividends: int, total_employment: int, ani: int
) -> dict:
    """Core dividend tax computation for a given dividend amount.
    Returns a dict with all band and tax values plus allowance breakdown.
    """
    pa, _ = calc_personal_allowance(ani)

    taxable_employment = max(0, total_employment - pa)

    dividend_allowance = min(dividends, DIVIDEND_ALLOWANCE)
    remaining_dividends = max(0, dividends - dividend_allowance)

    basic_consumed_by_employment = min(taxable_employment, _BASIC_BAND_WIDTH)
    basic_band_remaining = _BASIC_BAND_WIDTH - basic_consumed_by_employment

    allowance_in_basic = min(dividend_allowance, basic_band_remaining)
    basic_for_taxable_dividends = basic_band_remaining - allowance_in_basic

    div_basic_band = min(remaining_dividends, basic_for_taxable_dividends)
    div_basic_tax = round(div_basic_band * DIVIDEND_BASIC_RATE)

    remaining_after_basic = max(0, remaining_dividends - div_basic_band)

    higher_consumed_by_employment = max(
        0,
        min(taxable_employment, _BASIC_BAND_WIDTH + _HIGHER_BAND_WIDTH)
        - _BASIC_BAND_WIDTH,
    )
    higher_band_remaining = _HIGHER_BAND_WIDTH - higher_consumed_by_employment

    div_higher_band = min(remaining_after_basic, higher_band_remaining)
    div_higher_tax = round(div_higher_band * DIVIDEND_HIGHER_RATE)

    div_additional_band = max(0, remaining_after_basic - div_higher_band)
    div_additional_tax = round(div_additional_band * DIVIDEND_ADDITIONAL_RATE)

    total_tax = div_basic_tax + div_higher_tax + div_additional_tax

    return {
        "dividend_allowance": dividend_allowance,
        "taxable_dividends": remaining_dividends,
        "basic_band": div_basic_band,
        "basic_tax": div_basic_tax,
        "higher_band": div_higher_band,
        "higher_tax": div_higher_tax,
        "additional_band": div_additional_band,
        "additional_tax": div_additional_tax,
        "total_tax": total_tax,
    }


def calc_dividend_tax(
    dividends: int,
    salary: int,
    existing_income: float = 0,
    existing_dividends: float = 0,
) -> DividendTaxResult:
    """Tax on dividends, stacked on top of salary (and optional existing income).
    Dividend Tax: https://www.gov.uk/tax-on-dividends
    Income Tax: https://www.gov.uk/income-tax-rates (band limits used for stacking)

    *existing_income* is income already earned in the current tax year
    (e.g. from a previous contract). It consumes Personal Allowance and
    rate bands before *salary* and dividends are considered.

    *existing_dividends* is dividends already received in this tax year.
    They consume the £500 dividend allowance and rate band space before
    the *dividends* being distributed now.

    - £500 dividend allowance at 0% (separate from Personal Allowance)
    - Basic rate: 10.75% (taxable income £0–£37,700)
    - Higher rate: 35.75% (taxable income £37,701–£125,140)
    - Additional rate: 39.35% (taxable income above £125,140)
    - Personal Allowance consumed by salary + existing_income first.
    - Adjusted net income = salary + existing_income + dividends + existing_dividends
      determines PA taper.

    >>> res = calc_dividend_tax(40000, 12570)
    >>> res.total_tax
    4821
    """
    total_employment = salary + existing_income
    total_dividends = dividends + existing_dividends

    ani = calc_adjusted_net_income(
        employment_income=total_employment, dividend_income=total_dividends
    )

    # Compute on combined (existing + new) and on existing alone, then diff
    combined = _compute_dividend_tax_bands(
        round(dividends + existing_dividends), total_employment, ani
    )

    if existing_dividends:
        existing = _compute_dividend_tax_bands(
            round(existing_dividends), total_employment, ani
        )
        result = {
            "dividend_allowance": combined["dividend_allowance"] - existing["dividend_allowance"],
            "taxable_dividends": combined["taxable_dividends"] - existing["taxable_dividends"],
            "basic_band": combined["basic_band"] - existing["basic_band"],
            "basic_tax": combined["basic_tax"] - existing["basic_tax"],
            "higher_band": combined["higher_band"] - existing["higher_band"],
            "higher_tax": combined["higher_tax"] - existing["higher_tax"],
            "additional_band": combined["additional_band"] - existing["additional_band"],
            "additional_tax": combined["additional_tax"] - existing["additional_tax"],
            "total_tax": combined["total_tax"] - existing["total_tax"],
        }
    else:
        result = combined

    return DividendTaxResult(
        dividend_allowance=result["dividend_allowance"],
        taxable_dividends=result["taxable_dividends"],
        basic_band=result["basic_band"],
        basic_tax=result["basic_tax"],
        higher_band=result["higher_band"],
        higher_tax=result["higher_tax"],
        additional_band=result["additional_band"],
        additional_tax=result["additional_tax"],
        total_tax=result["total_tax"],
    )
