from payday.constants import MAX_SALARY_SACRIFICE, NI_SECONDARY_THRESHOLD


def calc_optimal_sacrifice_paye(
    gross: int,
    cap: int = 100_000,
) -> int:
    """Return the minimum annual salary sacrifice so that
    adjusted net income ≤ *cap* (default £100,000 — PA taper threshold).

    For PAYE, ANI = gross - sacrifice.  The minimum sacrifice is:
        sacrifice = max(0, gross - cap)
    """
    if cap <= 0:
        return 0
    return min(max(0, gross - cap), MAX_SALARY_SACRIFICE)


def inverse_solve_gross_salary(
    target_gross: int,
    include_er_pension: bool = True,
) -> int:
    """Return the budget needed to achieve *target_gross* via
    :meth:`InsideIR35Calculator.solve_gross_salary`.

    This is the mathematical inverse of ``solve_gross_salary``.

    Case A (gross ≤ 5,000):     budget = gross × 1.005
    Case B (gross > 5,000):     budget = gross × 1.155 − 750
    Case C (10k < gross ≤ 50,270):
        With pension:           budget = gross × 1.185 − 937.20
    Case D (gross > 50,270):
        With pension:           budget = gross × 1.155 + 570.90
    """
    if target_gross < 0:
        target_gross = 0

    if target_gross <= NI_SECONDARY_THRESHOLD:
        return round(target_gross * 1.005)

    if not include_er_pension:
        return round(target_gross * 1.155 - 750)

    # include_er_pension = True
    # Below PENSION_TRIGGER (10,000) → Case B, employer pension not triggered
    from payday.constants import PENSION_TRIGGER

    if target_gross <= PENSION_TRIGGER:
        return round(target_gross * 1.155 - 750)

    # Case C: 10000 < gross <= PENSION_QUALIFYING_UPPER_LIMIT (50270)
    from payday.constants import PENSION_QUALIFYING_UPPER_LIMIT

    if target_gross <= PENSION_QUALIFYING_UPPER_LIMIT:
        return round(target_gross * 1.185 - 937.20)

    # Case D: gross > 50270
    return round(target_gross * 1.155 + 570.90)


def calc_optimal_sacrifice_inside_ir35(
    annual_assignment: int,
    annual_margin: int,
    cap: int = 100_000,
    *,
    existing_income: float = 0,
    existing_dividends: float = 0,
) -> int:
    """Return the optimal annual salary sacrifice for an Inside IR35
    contractor so that adjusted net income ≤ *cap*.

    ANI = effective_gross + existing_income + existing_dividends.
    We want:  effective_gross ≤ cap − existing_income − existing_dividends.

    If existing income already breaches the cap, return 0 (can't fix).
    Otherwise compute the target gross, find the required budget via
    the inverse gross-salary solver, and work out the sacrifice.
    """
    if cap <= 0:
        return 0

    target_gross = max(0, cap - existing_income - existing_dividends)

    # If the target is too small to make a meaningful difference, give up
    if target_gross <= 500:
        return 0

    target_budget = inverse_solve_gross_salary(
        round(target_gross), include_er_pension=False
    )

    sacrifice = annual_assignment - target_budget - annual_margin
    # Clamp to feasible range: at least 0, at most budget − 1
    budget = annual_assignment - annual_margin
    sacrifice = max(0, min(sacrifice, budget - 1))
    sacrifice = min(sacrifice, MAX_SALARY_SACRIFICE)
    return sacrifice
