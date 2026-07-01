from payday.models import SalaryBreakdown


def format_gbp(amount: int) -> str:
    """Format integer pounds with commas and optional negative sign.

    >>> format_gbp(50000)
    '£50,000'
    >>> format_gbp(-3421)
    '-£3,421'
    """
    if amount < 0:
        return f"-£{-amount:,}"
    return f"£{amount:,}"


def _day_rate_context(breakdown: SalaryBreakdown) -> str:
    """Build day-rate suffix for modes with day rates."""
    day_rate = breakdown.inputs.get("day_rate")
    days = breakdown.inputs.get("effective_working_days") or breakdown.inputs.get(
        "working_days"
    )
    period = breakdown.inputs.get("contract_period")
    if day_rate and days:
        suffix = f", {period}" if period else ""
        return f"  ({format_gbp(day_rate)}/day × {days} days{suffix})"
    return ""


def _mode_title(breakdown: SalaryBreakdown) -> str:
    """Return a human-readable title for the mode."""
    titles = {
        "PAYE": "PAYE Salary Breakdown — 2026/27",
        "Inside IR35": "Inside IR35 (Umbrella) — 2026/27",
        "Outside IR35": "Outside IR35 (Ltd Co) — 2026/27",
    }
    title = titles.get(breakdown.mode, f"{breakdown.mode} — 2026/27")
    period = breakdown.inputs.get("contract_period")
    if period:
        title += f"  ({period})"
    existing = breakdown.inputs.get("existing_income")
    if existing:
        title += f"  [existing: {format_gbp(existing)}]"
    return title


def format_breakdown(breakdown: SalaryBreakdown) -> str:
    """Format a SalaryBreakdown into a terminal-friendly waterfall table."""
    lines = []
    width = 46
    col_gap = 2  # Min space between label end and amount start

    # ── Header ──
    lines.append("═" * width)
    lines.append(f"  {_mode_title(breakdown)}")
    lines.append("═" * width)

    for step in breakdown.steps:
        # If a subtotal, draw separator before it
        if step.is_subtotal:
            lines.append("  " + "─" * (width - 4))

        label = "  " * (step.indent + 1) + step.label + ":"
        amount = format_gbp(step.amount)

        # Day rate context for assignment/revenue lines
        day_ctx = ""
        if step.label in ("Assignment Rate", "Company Revenue") and breakdown.mode in (
            "Inside IR35",
            "Outside IR35",
        ):
            day_ctx = _day_rate_context(breakdown)

        # Outside IR35 Take-Home gets salary/dividend breakdown
        extra = ""
        if step.label == "Take-Home" and breakdown.mode == "Outside IR35":
            salary = breakdown.inputs.get("salary", 12570)
            net_divs = breakdown.annual_take_home - salary
            extra = f"    (Salary: {format_gbp(salary)}  |  Dividends: {format_gbp(net_divs)})"

        # Calculate padding to right-align the amount
        content = amount + day_ctx
        padding = max(col_gap, width - len(label) - len(content))

        if extra:
            lines.append(f"{label}{' ' * (padding)}{content}")
            lines.append(extra)
        else:
            lines.append(f"{label}{' ' * (padding)}{content}")

    lines.append("═" * width)
    return "\n".join(lines)
