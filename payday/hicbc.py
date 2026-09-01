# hicbc.py — High Income Child Benefit Charge (2026/27)
# Source: https://www.gov.uk/child-benefit-tax-charge
#
# HICBC claws back Child Benefit when the higher earner's Adjusted Net
# Income (ANI) exceeds £60,000, with 1% charge per £200 above £60k
# (ITEPA s.681C), i.e. linearly from 0% at £60k to 100% at £80k.
# Per s.681C(3) the percentage and the final charge are each rounded
# *down* to the nearest whole number/pound. The charge is collected
# via Self Assessment on the higher earner.

from payday.constants import (
    CHILD_BENEFIT_ADDITIONAL_CHILD_WEEKLY,
    CHILD_BENEFIT_FIRST_CHILD_WEEKLY,
    HICBC_LOWER_THRESHOLD,
    HICBC_UPPER_THRESHOLD,
    PA_TAPER_THRESHOLD,
)
from payday.models import HICBCResult, StepLine


def child_benefit_annual(num_children: int = 1) -> int:
    """Annual Child Benefit amount for *num_children* (weekly × 52).

    The weekly award × 52 is rounded *down* to the nearest pound as an
    approximation; the HICBC charge itself is always floored per
    ITEPA s.681C(3) (see also the LITRG step-by-step example).
    """
    if num_children < 1:
        return 0
    weekly = (
        CHILD_BENEFIT_FIRST_CHILD_WEEKLY
        + (num_children - 1) * CHILD_BENEFIT_ADDITIONAL_CHILD_WEEKLY
    )
    return int(weekly * 52)


def hicbc_charge_rate(ani: int | float) -> float:
    """Charge as fraction of Child Benefit (0.0–1.0) for a given ANI.

    0% at/under £60k, 100% at/over £80k, 1% per *complete* £200 in
    between — i.e. floor division, per ITEPA s.681C(3)(b) ("rounded
    down to the nearest whole number").

    >>> hicbc_charge_rate(60000)
    0.0
    >>> hicbc_charge_rate(70000)
    0.5
    >>> hicbc_charge_rate(80000)
    1.0
    """
    if ani <= HICBC_LOWER_THRESHOLD:
        return 0.0
    if ani >= HICBC_UPPER_THRESHOLD:
        return 1.0
    # HMRC: 1% per complete £200 → floor, not round
    excess = int(ani) - HICBC_LOWER_THRESHOLD
    pct = excess // 200  # complete £200 increments
    return pct * 0.01


def calc_hicbc(
    ani: int | float,
    annual_benefit: int | float | None = None,
    *,
    num_children: int = 1,
) -> int:
    """HICBC charge in £ for a given ANI.

    *annual_benefit* if provided overrides *num_children*.
    Per ITEPA s.681C(3)(a) the charge is rounded *down* to the nearest pound.
    """
    if annual_benefit is None:
        annual_benefit = child_benefit_annual(num_children)
    rate = hicbc_charge_rate(ani)
    return int(annual_benefit * rate)


def hicbc_effective_marginal_rate(
    ani_before: int,
    ani_after: int,
    annual_benefit: int | float | None = None,
    *,
    num_children: int = 1,
) -> float:
    """Extra effective marginal rate from HICBC between two ANIs.

    Public utility to substantiate the README's ~47% (1 child) / ~56%
    (3 children) effective-marginal claims when 40% higher-rate IT is
    combined with the HICBC clawback over the £60k–£80k band. Not used
    in the main calculation path — the charge itself is advisory.

    >>> round(hicbc_effective_marginal_rate(60000, 80000, num_children=1) * 100)
    7
    """
    if annual_benefit is None:
        annual_benefit = child_benefit_annual(num_children)
    if ani_before == ani_after:
        return 0.0
    charge_before = calc_hicbc(ani_before, annual_benefit)
    charge_after = calc_hicbc(ani_after, annual_benefit)
    return (charge_after - charge_before) / (ani_after - ani_before)


def recommended_ani_cap(has_child_benefit: bool) -> int:
    """Recommended ANI cap for salary-sacrifice auto targeting.

    * 100_000 — personal-allowance taper (default).
    * 60_000  — HICBC threshold when claiming Child Benefit.

    Callers that have an explicit ``income_target`` should honour it;
    this is only the *default* when none is supplied.

    >>> recommended_ani_cap(False)
    100000
    >>> recommended_ani_cap(True)
    60000
    """
    if has_child_benefit:
        return HICBC_LOWER_THRESHOLD
    return PA_TAPER_THRESHOLD


def hicbc_result_and_steps(
    ani: int,
    *,
    has_child_benefit: bool = False,
    num_children: int = 1,
) -> tuple[HICBCResult | None, list[StepLine]]:
    """Shared HICBC helper for all calculators.

    Returns ``(HICBCResult | None, list[StepLine])`` — the advisory
    result (or ``None`` when not applicable) and the waterfall step(s)
    to append. Single place to keep labels, thresholds, and rounding
    consistent across the four calculation modes.
    """
    if not has_child_benefit:
        return None, []

    annual_benefit = child_benefit_annual(num_children)
    charge_rate = hicbc_charge_rate(ani)
    charge = calc_hicbc(ani, annual_benefit)

    result = HICBCResult(
        ani=ani,
        has_child_benefit=True,
        lower_threshold=HICBC_LOWER_THRESHOLD,
        upper_threshold=HICBC_UPPER_THRESHOLD,
        charge_rate=charge_rate,
        annual_benefit=annual_benefit,
        charge=charge,
    )

    if charge_rate == 0:
        step = StepLine(
            f"Child Benefit (HICBC 0% — ANI £{ani:,} ≤ £{HICBC_LOWER_THRESHOLD:,}, advisory — not included in take-home)",
            0,
            indent=1,
        )
    elif charge_rate < 1.0:
        step = StepLine(
            f"Child Benefit (HICBC {charge_rate:.0%} — £{charge:,} of £{annual_benefit:,} clawed back, advisory — not included in take-home)",
            0,
            indent=1,
        )
    else:
        step = StepLine(
            f"Child Benefit (HICBC 100% — £{annual_benefit:,} clawed back at ANI £{ani:,}, advisory — not included in take-home)",
            0,
            indent=1,
        )

    return result, [step]


def apply_hicbc_inputs(
    inputs: dict,
    hicbc_result: HICBCResult | None,
    has_child_benefit: bool,
) -> None:
    """Populate HICBC-related keys in a calculator's ``inputs`` dict.

    Centralises the 3-line fragment duplicated across the four
    calculators; ``hicbc_result`` is always present when
    ``has_child_benefit`` is True.
    """
    if has_child_benefit and hicbc_result is not None:
        inputs["has_child_benefit"] = True
        inputs["hicbc_charge"] = hicbc_result.charge
        inputs["hicbc_rate"] = hicbc_result.charge_rate
