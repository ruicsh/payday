MONTH_NAMES: dict[int, str] = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}

_TAX_YEAR_START_CALENDAR = 2026


def months_in_tax_year(start_month: int) -> int:
    """Number of complete earnings months remaining in the 2026/27 tax year
    from *start_month* (1=Jan...12=Dec) through March.

    The tax year runs April 6 – April 5. The 12 earnings months are
    April through March.
    """
    if not 1 <= start_month <= 12:
        raise ValueError(f"start_month must be 1-12, got {start_month}")

    # Position in the tax-year earnings calendar:
    #   Apr(1)  May(2)  Jun(3)  Jul(4)  Aug(5)  Sep(6)
    #   Oct(7)  Nov(8)  Dec(9)  Jan(10) Feb(11) Mar(12)
    if start_month >= 4:
        position = start_month - 3
    else:
        position = start_month + 9

    return 12 - position + 1


def pro_rate_days(annual_days: int, months: int) -> int:
    """Pro-rate *annual_days* across *months* in a 12-month tax year."""
    if not 1 <= months <= 12:
        raise ValueError(f"months must be 1-12, got {months}")
    return round(annual_days * months / 12)


def pro_rate_contract(
    working_days: int, start_month: int | None
) -> tuple[int, int, str | None]:
    """Compute contract months, effective days, and display label.

    Returns (tax_year_months, effective_days, contract_period_label_or_None).
    When *start_month* is None, returns full-year values.
    """
    if start_month is None:
        return 12, working_days, None
    months = months_in_tax_year(start_month)
    return (
        months,
        pro_rate_days(working_days, months),
        contract_period_label(start_month, months),
    )


def contract_period_label(start_month: int, months: int) -> str:
    """Human-readable label like 'Aug 2026–Apr 2027 (8 months)'."""
    cal_year = (
        _TAX_YEAR_START_CALENDAR if start_month >= 4 else _TAX_YEAR_START_CALENDAR + 1
    )
    end_year = _TAX_YEAR_START_CALENDAR + 1
    suffix = "month" if months == 1 else "months"
    return f"{MONTH_NAMES[start_month]} {cal_year}–Apr {end_year} ({months} {suffix})"
