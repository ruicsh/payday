from payday.constants import (
    NI_CATEGORIES,
    NI_CLASS4_LOWER_PROFITS_LIMIT,
    NI_CLASS4_MAIN_RATE,
    NI_CLASS4_UPPER_PROFITS_LIMIT,
    NI_CLASS4_UPPER_RATE,
    NI_EMPLOYER_RATE,
    NI_PRIMARY_THRESHOLD,
    NI_SECONDARY_THRESHOLD,
    NI_UPPER_EARNINGS_LIMIT,
)
from payday.models import Class4NIResult, EmployeeNIResult, EmployerNIResult


def _ni_category_params(category: str) -> dict[str, float]:
    key = category.upper()
    if key not in NI_CATEGORIES:
        raise ValueError(
            f"Unknown NI category '{category}'. "
            f"Expected one of {', '.join(sorted(NI_CATEGORIES))}"
        )
    return NI_CATEGORIES[key]


def calc_employee_ni(salary: int, category: str = "A") -> EmployeeNIResult:
    """Employee Class 1 NI (2026/27).
    Employee NI: https://www.gov.uk/government/publications/rates-and-allowances-national-insurance-contributions/rates-and-allowances-national-insurance-contributions
    Category letters: https://www.gov.uk/national-insurance-rates-letters

    Category A (standard): 0% to PT, 8% PT-UEL, 2% above UEL
    Category B (married women/widows): 1.85% PT-UEL, 2% above
    Category C (over State Pension age): 0% (no employee NI)
    Category Z (under-21 deferment): 2% above PT

    >>> calc_employee_ni(50000).total_ni
    2994
    >>> calc_employee_ni(50000, "B").total_ni
    692
    >>> calc_employee_ni(50000, "C").total_ni
    0
    """
    params = _ni_category_params(category)
    main_rate = float(params["employee_main_rate"])
    upper_rate = float(params["employee_upper_rate"])

    below_pt = min(salary, NI_PRIMARY_THRESHOLD)

    main_band = max(0, min(salary, NI_UPPER_EARNINGS_LIMIT) - NI_PRIMARY_THRESHOLD)
    main_ni = round(main_band * main_rate)

    upper_band = max(0, salary - NI_UPPER_EARNINGS_LIMIT)
    upper_ni = round(upper_band * upper_rate)

    total_ni = main_ni + upper_ni

    # Zero-rate categories (e.g. C — over State Pension age) owe no employee
    # NI: all earnings sit below the chargeable threshold (below_pt = salary)
    # and every chargeable band is zero.
    if main_rate == 0.0 and upper_rate == 0.0:
        below_pt = salary
        main_band = 0
        main_ni = 0
        upper_band = 0
        upper_ni = 0
        total_ni = 0

    return EmployeeNIResult(
        below_pt=below_pt,
        main_band=main_band,
        main_ni=main_ni,
        upper_band=upper_band,
        upper_ni=upper_ni,
        total_ni=total_ni,
    )


def calc_employer_ni(gross_salary: int) -> EmployerNIResult:
    """Employer NI on gross salary (2026/27).
    Employer NI: https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027

    - 0% on earnings up to £5,000
    - 15% on earnings above £5,000

    >>> calc_employer_ni(50000).total_er_ni
    6750
    """
    below_st = min(gross_salary, NI_SECONDARY_THRESHOLD)
    above_st = max(0, gross_salary - NI_SECONDARY_THRESHOLD)
    total_er_ni = round(above_st * NI_EMPLOYER_RATE)

    return EmployerNIResult(
        below_st=below_st, above_st=above_st, total_er_ni=total_er_ni
    )


def calc_class4_ni(
    profit: int | float,
    existing_self_employment: float = 0,
) -> Class4NIResult:
    """Self-employed Class 4 National Insurance (2026/27).
    Self-employed NI rates: https://www.gov.uk/self-employed-national-insurance-rates
    Rates and allowances: https://www.gov.uk/government/publications/rates-and-allowances-national-insurance-contributions/rates-and-allowances-national-insurance-contributions

    - 0% on profits up to £12,570 (Lower Profits Limit)
    - 6% on £12,571 to £50,270
    - 2% on profits above £50,270

    Class 2 is treated as paid above the Small Profits Threshold (£7,105)
    since 6 Apr 2024 — no compulsory charge — so only Class 4 is
    included in take-home. Voluntary Class 2 (£3.65/week) below the
    threshold is not modelled.

    *existing_self_employment* is self-employment profit already earned
    this tax year. It consumes the remaining Class 4 bands — the
    returned result is only the NI attributable to *profit*.

    >>> calc_class4_ni(30000).total_ni
    1046
    >>> calc_class4_ni(75000).total_ni
    2757
    >>> calc_class4_ni(10000).total_ni
    0
    """
    total = profit + existing_self_employment
    existing = existing_self_employment

    def _main_band(amount: float) -> float:
        return max(
            0.0,
            min(amount, NI_CLASS4_UPPER_PROFITS_LIMIT) - NI_CLASS4_LOWER_PROFITS_LIMIT,
        )

    def _upper_band(amount: float) -> float:
        return max(0.0, amount - NI_CLASS4_UPPER_PROFITS_LIMIT)

    total_main = _main_band(total)
    existing_main = _main_band(existing)
    main_band = total_main - existing_main
    main_ni = round(main_band * NI_CLASS4_MAIN_RATE)

    total_upper = _upper_band(total)
    existing_upper = _upper_band(existing)
    upper_band = total_upper - existing_upper
    upper_ni = round(upper_band * NI_CLASS4_UPPER_RATE)

    below_lpl = min(round(total), NI_CLASS4_LOWER_PROFITS_LIMIT) - min(
        round(existing), NI_CLASS4_LOWER_PROFITS_LIMIT
    )
    # Clamp below_lpl to profit when profit is small
    if profit <= NI_CLASS4_LOWER_PROFITS_LIMIT:
        below_lpl = (
            round(min(profit, NI_CLASS4_LOWER_PROFITS_LIMIT - existing))
            if existing < NI_CLASS4_LOWER_PROFITS_LIMIT
            else 0
        )
        below_lpl = max(0, below_lpl)

    total_ni = main_ni + upper_ni

    return Class4NIResult(
        below_lpl=round(below_lpl),
        main_band=round(main_band),
        main_ni=main_ni,
        upper_band=round(upper_band),
        upper_ni=upper_ni,
        total_ni=total_ni,
    )
