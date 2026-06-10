from payday.constants import (
    CT_SMALL_PROFITS_RATE,
    CT_MAIN_RATE,
    CT_LOWER_LIMIT,
    CT_UPPER_LIMIT,
    CT_MARGINAL_RELIEF_FRACTION,
)
from payday.models import CorporationTaxResult


def calc_corporation_tax(profit: int) -> CorporationTaxResult:
    """Corporation Tax with Marginal Relief (financial year 2026).
    Source: https://www.gov.uk/corporation-tax-rates
    Legislation: Finance Act 2021, Schedule 1 (inserting CTA10/Part 3A)
    HMRC Manual: CTM03925 (Marginal Relief formula)

    The calculation follows CTA10/S18B formula: (F x (U - A)) x (N / A)
    where:
    - F = standard marginal relief fraction (3/200)
    - U = upper limit (£250,000)
    - A = augmented profits
    - N = taxable total profits

    Note: This implementation assumes N = A (no exempt distributions).

    - 19% if profit ≤ £50,000 (Small Profits Rate)
    - 25% - relief if £50,000 < profit ≤ £250,000 (Marginal Relief)
    - 25% if profit > £250,000 (Main Rate)

    >>> res = calc_corporation_tax(100000)
    >>> res.total_ct
    22750
    """
    if profit <= 0:
        return CorporationTaxResult(0, 0, 0, 0)

    if profit <= CT_LOWER_LIMIT:
        total_ct = round(profit * CT_SMALL_PROFITS_RATE)
        return CorporationTaxResult(profit, total_ct, 0, total_ct)

    full_rate_tax = round(profit * CT_MAIN_RATE)

    if profit <= CT_UPPER_LIMIT:
        marginal_relief = round((CT_UPPER_LIMIT - profit) * CT_MARGINAL_RELIEF_FRACTION)
        total_ct = full_rate_tax - marginal_relief
        return CorporationTaxResult(profit, full_rate_tax, marginal_relief, total_ct)

    return CorporationTaxResult(profit, full_rate_tax, 0, full_rate_tax)
