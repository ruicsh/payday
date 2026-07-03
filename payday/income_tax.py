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


def calc_adjusted_net_income(
    employment_income: float = 0,
    self_employment_income: int = 0,
    property_income: int = 0,
    savings_interest: int = 0,
    dividend_income: float = 0,
    pension_income: int = 0,
    other_taxable_income: int = 0,
    gross_pension_contributions: int = 0,
    trading_losses: int = 0,
    gift_aid_donations: int = 0,
    relief_at_source_pension: int = 0,
) -> int:
    """Compute adjusted net income (ANI) for personal allowance tapering.
    https://www.gov.uk/guidance/adjusted-net-income

    Per HMRC guidance:
      Step 1: Sum all taxable income - gross pension contributions - losses.
      Step 2: Subtract grossed-up Gift Aid donations (amount x 1.25).
      Step 3: Subtract grossed-up relief-at-source pension (amount x 1.25).

    >>> calc_adjusted_net_income(employment_income=50000)
    50000
    >>> # Bill: income 115k (85k SE + 20k property + 10k interest), gross pension 10k
    >>> calc_adjusted_net_income(
    ...     self_employment_income=85000, property_income=20000,
    ...     savings_interest=10000, gross_pension_contributions=10000,
    ... )
    105000
    >>> # Clara: income 70k (65k emp + 5k interest), gross pension 4750, Gift Aid 1000
    >>> calc_adjusted_net_income(
    ...     employment_income=65000, savings_interest=5000,
    ...     gross_pension_contributions=4750, gift_aid_donations=1000,
    ... )
    64000
    """
    net_income = (
        employment_income
        + self_employment_income
        + property_income
        + savings_interest
        + dividend_income
        + pension_income
        + other_taxable_income
        - gross_pension_contributions
        - trading_losses
    )

    ani = net_income
    if gift_aid_donations:
        ani -= round(gift_aid_donations * 1.25)
    if relief_at_source_pension:
        ani -= round(relief_at_source_pension * 1.25)

    return round(ani)


def calc_personal_allowance(adjusted_net_income: int | float) -> tuple[int, bool]:
    """Return (personal_allowance, tapered_flag).
    Income Tax: https://www.gov.uk/income-tax-rates
    ANI: https://www.gov.uk/guidance/adjusted-net-income

    Standard allowance £12,570. Reduces by £1 per £2 over £100,000.
    Zero at £125,140 or above.

    >>> calc_personal_allowance(50000)
    (12570, False)
    >>> calc_personal_allowance(110000)
    (7570, True)
    >>> calc_personal_allowance(125140)
    (0, True)
    """
    if adjusted_net_income <= PA_TAPER_THRESHOLD:
        return PERSONAL_ALLOWANCE, False

    reduction = int((adjusted_net_income - PA_TAPER_THRESHOLD) * PA_TAPER_RATE)
    pa = max(0, PERSONAL_ALLOWANCE - reduction)
    return pa, True


def _tax_components(taxable: float, basic_band_width: int, higher_band_limit: int):
    """Compute tax band breakdown for a taxable income amount."""
    basic = min(taxable, basic_band_width)
    higher = max(0, min(taxable, higher_band_limit) - basic_band_width)
    additional = max(0, taxable - higher_band_limit)
    basic_tax = round(basic * BASIC_RATE)
    higher_tax = round(higher * HIGHER_RATE)
    additional_tax = round(additional * ADDITIONAL_RATE)
    return basic, higher, additional, basic_tax, higher_tax, additional_tax


def calc_income_tax(
    salary: int, personal_allowance: int, existing_income: float = 0
) -> IncomeTaxResult:
    """Compute full IncomeTaxResult for a given salary and PA.
    Income Tax: https://www.gov.uk/income-tax-rates

    *existing_income* accounts for income already earned in this tax year.
    It reduces the remaining Personal Allowance and rate bands available
    for *salary*.

    Bands (2026/27):
      - 0%: £0 to personal_allowance
      - 20%: personal_allowance+1 to £50,270
      - 40%: £50,271 to £125,140
      - 45%: above £125,140

    >>> res = calc_income_tax(50000, 12570)
    >>> res.total_tax
    7486
    """
    basic_band_width = BASIC_RATE_BAND_LIMIT - PERSONAL_ALLOWANCE  # 37,700
    higher_band_limit = HIGHER_RATE_BAND_LIMIT  # 125,140

    total_taxable = max(0, salary + existing_income - personal_allowance)
    existing_taxable = max(0, existing_income - personal_allowance)

    # Tax on combined (existing + new) and on existing alone
    bc, hc, ac, btc, htc, atc = _tax_components(
        total_taxable, basic_band_width, higher_band_limit
    )
    be, he, ae, bte, hte, ate = _tax_components(
        existing_taxable, basic_band_width, higher_band_limit
    )

    # Band breakdown for the new salary only (difference of combined vs existing)
    basic_band = bc - be
    higher_band = hc - he
    additional_band = ac - ae
    basic_tax = round(basic_band * BASIC_RATE)
    higher_tax = round(higher_band * HIGHER_RATE)
    additional_tax = round(additional_band * ADDITIONAL_RATE)

    # Total derived from band sum, consistent with per-band rounding
    total_tax = basic_tax + higher_tax + additional_tax

    # Remaining PA for display
    remaining_pa = max(0, personal_allowance - existing_income)
    taxable_income = max(0, salary - remaining_pa)

    return IncomeTaxResult(
        personal_allowance=personal_allowance,
        tapered=(personal_allowance < PERSONAL_ALLOWANCE),
        taxable_income=round(taxable_income),
        basic_band=round(basic_band),
        higher_band=round(higher_band),
        additional_band=round(additional_band),
        basic_tax=basic_tax,
        higher_tax=higher_tax,
        additional_tax=additional_tax,
        total_tax=total_tax,
    )
