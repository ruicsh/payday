from payday.constants import (
    ANNUAL_ALLOWANCE,
    AA_TAPER_ADJUSTED_INCOME,
    AA_TAPER_MIN,
    AA_TAPER_THRESHOLD_INCOME,
)
from payday.models import AnnualAllowanceResult


def calc_annual_allowance(
    threshold_income: int | float,
    adjusted_income: int | float,
) -> AnnualAllowanceResult:
    """Calculate the tapered Annual Allowance for 2026/27.

    Annual Allowance: https://www.gov.uk/tax-on-your-private-pension/annual-allowance
    Tapered Annual Allowance: https://www.gov.uk/guidance/pension-schemes-work-out-your-tapered-annual-allowance

    Rules (2026/27):
    - Standard allowance is £60,000.
    - Taper only applies when threshold income > £200,000
      AND adjusted income > £260,000.
    - Reduction is £1 for every £2 of adjusted income over £260,000.
    - Floored at £10,000.

    >>> calc_annual_allowance(150_000, 150_000).annual_allowance
    60000
    >>> calc_annual_allowance(150_000, 300_000).annual_allowance
    60000
    >>> calc_annual_allowance(210_000, 260_000).annual_allowance
    60000
    >>> calc_annual_allowance(210_000, 270_000).annual_allowance
    55000
    >>> calc_annual_allowance(300_000, 360_000).annual_allowance
    10000
    >>> calc_annual_allowance(360_000, 400_000).annual_allowance
    10000
    """
    threshold_income = round(threshold_income)
    adjusted_income = round(adjusted_income)

    if (
        threshold_income <= AA_TAPER_THRESHOLD_INCOME
        or adjusted_income <= AA_TAPER_ADJUSTED_INCOME
    ):
        return AnnualAllowanceResult(
            threshold_income=threshold_income,
            adjusted_income=adjusted_income,
            standard_allowance=ANNUAL_ALLOWANCE,
            annual_allowance=ANNUAL_ALLOWANCE,
            tapered=False,
        )

    reduction = int((adjusted_income - AA_TAPER_ADJUSTED_INCOME) * 0.5)
    tapered_allowance = max(AA_TAPER_MIN, ANNUAL_ALLOWANCE - reduction)

    return AnnualAllowanceResult(
        threshold_income=threshold_income,
        adjusted_income=adjusted_income,
        standard_allowance=ANNUAL_ALLOWANCE,
        annual_allowance=tapered_allowance,
        tapered=True,
    )


def calc_threshold_income(
    total_income: int | float,
    salary_sacrifice: int | float = 0,
    relief_at_source_pension: int | float = 0,
) -> int:
    """Compute threshold income for AA taper.

    Threshold income: https://www.gov.uk/guidance/pension-schemes-work-out-your-tapered-annual-allowance

    Threshold income = total taxable income
                       + salary sacrifice / flexible remuneration add-back
                       - grossed-up relief-at-source pension contributions.

    >>> calc_threshold_income(300_000, salary_sacrifice=60_000)
    360000
    >>> calc_threshold_income(300_000, salary_sacrifice=0, relief_at_source_pension=10_000)
    287500
    """
    grossed_relief = (
        round(relief_at_source_pension * 1.25) if relief_at_source_pension else 0
    )
    return round(total_income + salary_sacrifice - grossed_relief)


def calc_adjusted_income(
    threshold_income: int | float,
    pension_input_amount: int | float = 0,
) -> int:
    """Compute adjusted income for AA taper.

    Adjusted income = threshold income + total pension input amounts
    (employer contributions + all personal contributions including
    salary sacrifice and grossed-up relief-at-source).

    >>> calc_adjusted_income(300_000, 60_000)
    360000
    """
    return round(threshold_income + pension_input_amount)


def find_max_pension_for_threshold(
    threshold_income: int | float,
    *,
    get_adjusted_for_pension=None,
) -> int:
    """Return the maximum pension contribution that does not exceed the tapered AA.

    For the common case where adjusted = threshold + pension, solves
    pension <= AA(threshold, threshold + pension) analytically.

    When a custom ``get_adjusted_for_pension`` callable is supplied it
    will be used to compute adjusted income for each candidate pension
    (e.g. Inside IR35 where adjusted depends on the solved gross).

    Uses binary search over [0, ANNUAL_ALLOWANCE] so integer rounding
    is handled correctly regardless of formula.
    """
    threshold_income = round(threshold_income)

    # Fast path: if threshold <= 200k, no taper ever triggers.
    if threshold_income <= AA_TAPER_THRESHOLD_INCOME:
        return ANNUAL_ALLOWANCE

    if get_adjusted_for_pension is None:

        def _default_adjusted(p: int) -> int:
            return round(threshold_income + p)

        get_adjusted = _default_adjusted
    else:
        get_adjusted = get_adjusted_for_pension

    lo, hi = 0, ANNUAL_ALLOWANCE
    best = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        adjusted = get_adjusted(mid)
        aa = calc_annual_allowance(threshold_income, adjusted).annual_allowance
        if mid <= aa:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best
