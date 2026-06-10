from payday.constants import (
    PERSONAL_ALLOWANCE,
    PA_TAPER_THRESHOLD,
    PA_TAPER_RATE,
    BASIC_RATE_BAND_LIMIT,
    HIGHER_RATE_BAND_LIMIT,
    BASIC_RATE,
    HIGHER_RATE,
    ADDITIONAL_RATE,
)
from payday.models import IncomeTaxResult


def calc_personal_allowance(salary: int) -> tuple[int, bool]:
    """Return (personal_allowance, tapered_flag).

    Standard allowance £12,570. Reduces by £1 per £2 over £100,000.
    Zero at £125,140 or above.

    >>> calc_personal_allowance(50000)
    (12570, False)
    >>> calc_personal_allowance(110000)
    (7570, True)
    >>> calc_personal_allowance(125140)
    (0, True)
    """
    if salary <= PA_TAPER_THRESHOLD:
        return PERSONAL_ALLOWANCE, False

    reduction = int((salary - PA_TAPER_THRESHOLD) * PA_TAPER_RATE)
    pa = max(0, PERSONAL_ALLOWANCE - reduction)
    return pa, True


def calc_income_tax(salary: int, personal_allowance: int) -> IncomeTaxResult:
    """Compute full IncomeTaxResult for a given salary and PA.

    Bands (2026/27):
      - 0%: £0 to personal_allowance
      - 20%: personal_allowance+1 to £50,270
      - 40%: £50,271 to £125,140
      - 45%: above £125,140

    >>> res = calc_income_tax(50000, 12570)
    >>> res.total_tax
    7486
    """
    taxable_income = max(0, salary - personal_allowance)

    # Calculate bands relative to 0, but adjusted by PA
    # Basic rate ends at 50,270. If PA is 12,570, basic band is 37,700 wide.
    # HMRC bands are defined as:
    # Basic: £0 to £37,700 taxable
    # Higher: £37,701 to £125,140 taxable (if PA is 0)
    # Actually, the thresholds 50,270 and 125,140 are the top of the bands.

    # Taxable income bands (fixed, independent of PA):
    #   20%: first £37,700 of taxable income
    #   40%: £37,701 to £125,140 of taxable income
    #   45%: above £125,140 of taxable income

    basic_band_width = BASIC_RATE_BAND_LIMIT - PERSONAL_ALLOWANCE  # 37,700
    higher_band_limit = HIGHER_RATE_BAND_LIMIT  # 125,140

    # Basic Band (20%)
    basic_band = min(taxable_income, basic_band_width)
    basic_tax = round(basic_band * BASIC_RATE)

    # Higher Band (40%)
    higher_band = max(0, min(taxable_income, higher_band_limit) - basic_band_width)
    higher_tax = round(higher_band * HIGHER_RATE)

    # Additional Band (45%)
    additional_band = max(0, taxable_income - higher_band_limit)
    additional_tax = round(additional_band * ADDITIONAL_RATE)

    total_tax = basic_tax + higher_tax + additional_tax

    return IncomeTaxResult(
        personal_allowance=personal_allowance,
        tapered=(salary > PA_TAPER_THRESHOLD),
        taxable_income=taxable_income,
        basic_band=basic_band,
        basic_tax=basic_tax,
        higher_band=higher_band,
        higher_tax=higher_tax,
        additional_band=additional_band,
        additional_tax=additional_tax,
        total_tax=total_tax,
    )
