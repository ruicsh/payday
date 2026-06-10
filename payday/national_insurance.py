from payday.constants import (
    NI_PRIMARY_THRESHOLD,
    NI_UPPER_EARNINGS_LIMIT,
    NI_MAIN_RATE,
    NI_UPPER_RATE,
    NI_SECONDARY_THRESHOLD,
    NI_EMPLOYER_RATE,
)
from payday.models import EmployeeNIResult, EmployerNIResult


def calc_employee_ni(salary: int) -> EmployeeNIResult:
    """Employee Class 1 NI, Category A (2026/27).

    - 0% on earnings up to £12,570
    - 8% on £12,571 to £50,270
    - 2% on earnings above £50,270

    >>> res = calc_employee_ni(50000)
    >>> res.total_ni
    2994
    """
    below_pt = min(salary, NI_PRIMARY_THRESHOLD)

    main_band = max(0, min(salary, NI_UPPER_EARNINGS_LIMIT) - NI_PRIMARY_THRESHOLD)
    main_ni = round(main_band * NI_MAIN_RATE)

    upper_band = max(0, salary - NI_UPPER_EARNINGS_LIMIT)
    upper_ni = round(upper_band * NI_UPPER_RATE)

    total_ni = main_ni + upper_ni

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

    - 0% on earnings up to £5,000
    - 15% on earnings above £5,000

    >>> res = calc_employer_ni(50000)
    >>> res.total_er_ni
    6750
    """
    below_st = min(gross_salary, NI_SECONDARY_THRESHOLD)
    above_st = max(0, gross_salary - NI_SECONDARY_THRESHOLD)
    total_er_ni = round(above_st * NI_EMPLOYER_RATE)

    return EmployerNIResult(
        below_st=below_st, above_st=above_st, total_er_ni=total_er_ni
    )
