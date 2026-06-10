from payday.constants import (
    PENSION_TRIGGER,
    PENSION_QUALIFYING_LOWER_LIMIT,
    PENSION_QUALIFYING_UPPER_LIMIT,
    PENSION_EMPLOYEE_RATE,
    PENSION_EMPLOYER_RATE,
)
from payday.models import PensionResult


def calc_pension(salary: int) -> PensionResult:
    """Calculate auto-enrolment pension contributions.
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
