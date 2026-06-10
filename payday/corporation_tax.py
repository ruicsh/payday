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
    # Source: https://www.gov.uk/corporation-tax-rates

    - 19% if profit ≤ £50,000
    - 25% - relief if £50,000 < profit ≤ £250,000
      where relief = (250,000 - profit) × 3/200
    - 25% if profit > £250,000

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
