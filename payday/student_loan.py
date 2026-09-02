from payday.constants import (
    STUDENT_LOAN_PLAN1_THRESHOLD,
    STUDENT_LOAN_PLAN2_THRESHOLD,
    STUDENT_LOAN_PLAN4_THRESHOLD,
    STUDENT_LOAN_PLAN5_THRESHOLD,
    STUDENT_LOAN_POSTGRADUATE_THRESHOLD,
    STUDENT_LOAN_UNDERGRADUATE_RATE,
    STUDENT_LOAN_POSTGRADUATE_RATE,
)
from payday.models import StudentLoanResult

VALID_STUDENT_LOAN_PLANS: set[str] = {"plan1", "plan2", "plan4", "plan5"}

_PLAN_THRESHOLDS: dict[str, int] = {
    "plan1": STUDENT_LOAN_PLAN1_THRESHOLD,
    "plan2": STUDENT_LOAN_PLAN2_THRESHOLD,
    "plan4": STUDENT_LOAN_PLAN4_THRESHOLD,
    "plan5": STUDENT_LOAN_PLAN5_THRESHOLD,
}


def _above_threshold(
    income: int | float, threshold: int, existing_income: float = 0
) -> int:
    """Income from *income* that sits above *threshold* after existing income."""
    remaining_threshold = max(0, threshold - existing_income)
    return max(0, round(income - remaining_threshold))


def calc_student_loan(
    income: int | float,
    plan: str,
    existing_income: float = 0,
) -> StudentLoanResult:
    """Student Loan Plan 1/2/4/5 repayment (9% above threshold).
    Source: https://www.gov.uk/repaying-your-student-loan/what-you-pay

    *existing_income* is income already earned this tax year. It reduces
    the remaining threshold before the current *income* repays.

    >>> calc_student_loan(35000, "plan2").repayment
    505
    """
    if plan not in VALID_STUDENT_LOAN_PLANS:
        raise ValueError(f"Unknown student loan plan: '{plan}'")
    threshold = _PLAN_THRESHOLDS[plan]
    above = _above_threshold(income, threshold, existing_income)
    repayment = round(above * STUDENT_LOAN_UNDERGRADUATE_RATE)
    return StudentLoanResult(
        plan=plan,
        threshold=threshold,
        rate=STUDENT_LOAN_UNDERGRADUATE_RATE,
        income_above_threshold=above,
        repayment=repayment,
    )


def calc_postgraduate_loan(
    income: int | float,
    existing_income: float = 0,
) -> StudentLoanResult:
    """Postgraduate Loan (Plan 3) repayment (6% above £21,000; England & Wales only).
    Source: https://www.gov.uk/repaying-your-student-loan/what-you-pay

    Stacks on top of an undergraduate plan repayment. Postgraduate loans for
    Scotland and Northern Ireland are not Plan 3 — they repay under the Plan 4
    (Scotland) and Plan 1 (Northern Ireland) systems instead, combined with
    the undergraduate debt. Lifelong Learning Entitlement and Advanced Learner
    Loans also have no separate parameters: they repay on Plan 5 (post-Aug
    2023) or Plan 2 (pre-2023) terms.

    >>> calc_postgraduate_loan(30000).repayment
    540
    """
    threshold = STUDENT_LOAN_POSTGRADUATE_THRESHOLD
    above = _above_threshold(income, threshold, existing_income)
    repayment = round(above * STUDENT_LOAN_POSTGRADUATE_RATE)
    return StudentLoanResult(
        plan="postgraduate",
        threshold=threshold,
        rate=STUDENT_LOAN_POSTGRADUATE_RATE,
        income_above_threshold=above,
        repayment=repayment,
    )
