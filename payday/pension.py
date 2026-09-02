from payday.constants import (
    PENSION_TRIGGER,
    PENSION_QUALIFYING_LOWER_LIMIT,
    PENSION_QUALIFYING_UPPER_LIMIT,
    PENSION_EMPLOYEE_RATE,
    PENSION_EMPLOYER_RATE,
    RELIEF_AT_SOURCE_NET_RATE,
)
from payday.models import PensionResult


def employee_net_contribution(
    employee_contribution: int, method: str = "relief_at_source"
) -> int:
    """Member amount deducted from take-home for a gross employee contribution.

    For ``relief_at_source`` the member pays 80% from net pay and the
    provider claims 20% basic-rate relief
    (https://www.gov.uk/tax-on-your-private-pension/pension-tax-relief);
    for ``net_pay`` the member pays the full gross amount (deducted before
    tax). ``employee_contribution`` is the gross figure from :func:`calc_pension`.
    """
    if method == "relief_at_source":
        return round(employee_contribution * RELIEF_AT_SOURCE_NET_RATE)
    return employee_contribution


def ras_net_contribution(gross_employee: int) -> int:
    """Net member amount for a relief-at-source gross contribution (80%)."""
    return round(gross_employee * RELIEF_AT_SOURCE_NET_RATE)


def pension_tax_params(
    effective_gross: int, gross_employee: int, method: str
) -> tuple[int, int]:
    """Return ``(taxable_gross, band_extension)`` for the pension method.

    * ``net_pay``: taxable is reduced by the gross contribution, no extension.
    * ``relief_at_source``: full gross is taxable; basic-rate band extended
      by the gross contribution (HMRC extends 20%/21% band).
    """
    if method == "net_pay":
        return max(0, effective_gross - gross_employee), 0
    return effective_gross, gross_employee


def calc_pension(salary: int) -> PensionResult:
    """Calculate auto-enrolment pension contributions.
    Pension: https://www.gov.uk/workplace-pensions/what-you-your-employer-and-the-government-pay

    Rules:
    - If salary <= PENSION_TRIGGER, no auto-enrolment (eligible = False).
    - Qualifying earnings = Salary between LEL (£6,240) and UEL (£50,270).
    - Employee contribution = 5% of qualifying earnings.
    - Employer contribution = 3% of qualifying earnings.
    """
    if salary <= PENSION_TRIGGER:
        return PensionResult(
            eligible=False,
            qualifying_earnings=0,
            employee_contribution=0,
            employer_contribution=0,
        )

    # Qualifying earnings are capped between LEL and UEL
    basis = min(salary, PENSION_QUALIFYING_UPPER_LIMIT)
    qualifying_earnings = max(0, basis - PENSION_QUALIFYING_LOWER_LIMIT)

    employee_contribution = round(qualifying_earnings * PENSION_EMPLOYEE_RATE)
    employer_contribution = round(qualifying_earnings * PENSION_EMPLOYER_RATE)

    return PensionResult(
        eligible=True,
        qualifying_earnings=qualifying_earnings,
        employee_contribution=employee_contribution,
        employer_contribution=employer_contribution,
    )
