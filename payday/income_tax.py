from payday.constants import (
    PERSONAL_ALLOWANCE,
    PA_TAPER_THRESHOLD,
    PA_TAPER_RATE,
    BASIC_RATE_BAND_LIMIT,
    HIGHER_RATE_BAND_LIMIT,
    BASIC_RATE,
    HIGHER_RATE,
    ADDITIONAL_RATE,
    SCOTTISH_STARTER_BAND_LIMIT,
    SCOTTISH_BASIC_BAND_LIMIT,
    SCOTTISH_INTERMEDIATE_BAND_LIMIT,
    SCOTTISH_HIGHER_BAND_LIMIT,
    SCOTTISH_ADVANCED_BAND_LIMIT,
    SCOTTISH_STARTER_RATE,
    SCOTTISH_BASIC_RATE,
    SCOTTISH_INTERMEDIATE_RATE,
    SCOTTISH_HIGHER_RATE,
    SCOTTISH_ADVANCED_RATE,
    SCOTTISH_TOP_RATE,
)
from payday.models import IncomeTaxResult


def _normalise_region(region: str | None) -> str:
    if region == "scotland":
        return "scotland"
    return "rest_of_uk"


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


# Scottish thresholds expressed as taxable-income widths (threshold − PERSONAL_ALLOWANCE).
# Source: https://www.gov.uk/scottish-income-tax
_SCOT_STARTER_WIDTH = SCOTTISH_STARTER_BAND_LIMIT - PERSONAL_ALLOWANCE  # 3,967
_SCOT_BASIC_WIDTH = SCOTTISH_BASIC_BAND_LIMIT - SCOTTISH_STARTER_BAND_LIMIT  # 12,989
_SCOT_INTERMEDIATE_WIDTH = (
    SCOTTISH_INTERMEDIATE_BAND_LIMIT - SCOTTISH_BASIC_BAND_LIMIT
)  # 14,136
_SCOT_HIGHER_WIDTH = (
    SCOTTISH_HIGHER_BAND_LIMIT - SCOTTISH_INTERMEDIATE_BAND_LIMIT
)  # 31,338
_SCOT_ADVANCED_WIDTH = (
    SCOTTISH_ADVANCED_BAND_LIMIT - SCOTTISH_HIGHER_BAND_LIMIT
)  # 50,140
# Cumulative taxable-income upper bounds (inclusive widths).
# Source: https://www.gov.uk/scottish-income-tax
_SCOT_STARTER_UPPER = _SCOT_STARTER_WIDTH  # 3,967
_SCOT_BASIC_UPPER = _SCOT_STARTER_UPPER + _SCOT_BASIC_WIDTH  # 16,956
_SCOT_INTERMEDIATE_UPPER = _SCOT_BASIC_UPPER + _SCOT_INTERMEDIATE_WIDTH  # 31,092
_SCOT_HIGHER_UPPER = _SCOT_INTERMEDIATE_UPPER + _SCOT_HIGHER_WIDTH  # 62,430
_SCOT_ADVANCED_UPPER = _SCOT_HIGHER_UPPER + _SCOT_ADVANCED_WIDTH  # 112,570


def _tax_components_scotland(
    taxable: float,
) -> tuple[float, float, float, float, float, float]:
    """Scottish 6-band breakdown for a taxable income amount.
    Source: https://www.gov.uk/scottish-income-tax

    Bands (taxable income, i.e. income − PA):
      Starter 19%  : 0–3,967
      Basic 20%    : 3,968–16,956
      Intermediate : 16,957–31,092
      Higher 42%   : 31,093–62,430
      Advanced 45% : 62,431–112,570
      Top 48%      : >112,570

    Returns only band widths — the caller computes tax on the
    *difference* band (combined − existing) to avoid double rounding.
    """
    starter = min(taxable, _SCOT_STARTER_UPPER)
    basic = max(0, min(taxable, _SCOT_BASIC_UPPER) - _SCOT_STARTER_UPPER)
    intermediate = max(0, min(taxable, _SCOT_INTERMEDIATE_UPPER) - _SCOT_BASIC_UPPER)
    higher = max(0, min(taxable, _SCOT_HIGHER_UPPER) - _SCOT_INTERMEDIATE_UPPER)
    advanced = max(0, min(taxable, _SCOT_ADVANCED_UPPER) - _SCOT_HIGHER_UPPER)
    top = max(0, taxable - _SCOT_ADVANCED_UPPER)
    return starter, basic, intermediate, higher, advanced, top


def calc_income_tax(
    salary: int,
    personal_allowance: int,
    existing_income: float = 0,
    region: str | None = None,
) -> IncomeTaxResult:
    """Compute full IncomeTaxResult for a given salary and PA.
    Income Tax: https://www.gov.uk/income-tax-rates
    Scottish Income Tax: https://www.gov.uk/scottish-income-tax

    *existing_income* accounts for income already earned in this tax year.
    It reduces the remaining Personal Allowance and rate bands available
    for *salary*.
    *region* is ``"scotland"`` for Scottish rates, anything else (or None)
    for rest-of-UK (England/Wales/NI). Aliases ``england``/``wales``/
    ``northern_ireland`` normalise to rest_of_uk.

    rUK Bands (2026/27):
      - 0%: £0 to personal_allowance
      - 20%: personal_allowance+1 to £50,270
      - 40%: £50,271 to £125,140
      - 45%: above £125,140

    Scotland Bands (2026/27, non-savings non-dividend income):
      - 0%:        up to £12,570
      - 19% Starter:       £12,571–£16,537
      - 20% Basic:         £16,538–£29,526
      - 21% Intermediate:  £29,527–£43,662
      - 42% Higher:        £43,663–£75,000
      - 45% Advanced:      £75,001–£125,140
      - 48% Top:           over £125,140

    >>> res = calc_income_tax(50000, 12570)
    >>> res.total_tax
    7486
    """
    region = _normalise_region(region)
    is_scotland = region == "scotland"

    total_taxable = max(0, salary + existing_income - personal_allowance)
    existing_taxable = max(0, existing_income - personal_allowance)

    if is_scotland:
        sc, bc, ic, hc, ac, tc = _tax_components_scotland(total_taxable)
        se, be, ie, he, ae, te = _tax_components_scotland(existing_taxable)

        starter_band = sc - se
        basic_band = bc - be
        intermediate_band = ic - ie
        higher_band = hc - he
        advanced_band = ac - ae
        top_band = tc - te

        starter_tax = round(starter_band * SCOTTISH_STARTER_RATE)
        basic_tax = round(basic_band * SCOTTISH_BASIC_RATE)
        intermediate_tax = round(intermediate_band * SCOTTISH_INTERMEDIATE_RATE)
        higher_tax = round(higher_band * SCOTTISH_HIGHER_RATE)
        advanced_tax = round(advanced_band * SCOTTISH_ADVANCED_RATE)
        top_tax = round(top_band * SCOTTISH_TOP_RATE)

        total_tax = (
            starter_tax
            + basic_tax
            + intermediate_tax
            + higher_tax
            + advanced_tax
            + top_tax
        )
        # For rUK fields, basic/higher map to Scottish basic (20%) / higher (42%);
        # additional is unused for Scotland.
        additional_band = 0
        additional_tax = 0
    else:
        basic_band_width = BASIC_RATE_BAND_LIMIT - PERSONAL_ALLOWANCE  # 37,700
        higher_band_limit = HIGHER_RATE_BAND_LIMIT  # 125,140

        bc, hc, ac, *_ = _tax_components(
            total_taxable, basic_band_width, higher_band_limit
        )
        be, he, ae, *_ = _tax_components(
            existing_taxable, basic_band_width, higher_band_limit
        )

        basic_band = bc - be
        higher_band = hc - he
        additional_band = ac - ae
        basic_tax = round(basic_band * BASIC_RATE)
        higher_tax = round(higher_band * HIGHER_RATE)
        additional_tax = round(additional_band * ADDITIONAL_RATE)

        total_tax = basic_tax + higher_tax + additional_tax

        # Scotland-specific fields stay 0 for rUK.
        starter_band = 0
        starter_tax = 0
        intermediate_band = 0
        intermediate_tax = 0
        advanced_band = 0
        advanced_tax = 0
        top_band = 0
        top_tax = 0

    # Remaining PA for display
    remaining_pa = max(0, personal_allowance - existing_income)
    taxable_income = max(0, salary - remaining_pa)

    return IncomeTaxResult(
        personal_allowance=personal_allowance,
        tapered=(personal_allowance < PERSONAL_ALLOWANCE),
        taxable_income=round(taxable_income),
        basic_band=round(basic_band),
        basic_tax=basic_tax,
        higher_band=round(higher_band),
        higher_tax=higher_tax,
        additional_band=round(additional_band),
        additional_tax=additional_tax,
        total_tax=total_tax,
        region=region,
        starter_band=round(starter_band) if is_scotland else 0,
        starter_tax=starter_tax if is_scotland else 0,
        intermediate_band=round(intermediate_band) if is_scotland else 0,
        intermediate_tax=intermediate_tax if is_scotland else 0,
        advanced_band=round(advanced_band) if is_scotland else 0,
        advanced_tax=advanced_tax if is_scotland else 0,
        top_band=round(top_band) if is_scotland else 0,
        top_tax=top_tax if is_scotland else 0,
    )
