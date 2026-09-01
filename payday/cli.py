import sys
from collections.abc import Callable
from payday.config import VALID_MODES
from payday.constants import MAX_SALARY_SACRIFICE, PAYSTREAM_ADMIN_CHARGE_WEEKLY
from payday.calculators.optimal_sacrifice import (
    calc_optimal_sacrifice_inside_ir35,
    calc_optimal_sacrifice_paye,
)
from payday.calculators.paye import PAYECalculator
from payday.calculators.inside_ir35 import InsideIR35Calculator
from payday.calculators.outside_ir35 import OutsideIR35Calculator
from payday.calculators.sole_trader import SoleTraderCalculator
from payday.formatters import format_breakdown, format_gbp
from payday.tax_year import (
    contract_period_label,
    months_in_tax_year,
    working_days_in_contract_period,
    working_days_in_full_tax_year,
)


class SacrificeChoice(int):
    """Annual sacrifice amount that also carries its frequency.

    Subclasses :class:`int` so existing ``int`` comparisons keep working
    (``SacrificeChoice(50000, "monthly") == 50000``) while callers that
    need the frequency can read ``.frequency`` (``"monthly"`` or ``"daily"``).
    """

    frequency: str

    def __new__(cls, amount: int, frequency: str = "monthly") -> "SacrificeChoice":
        obj = int.__new__(cls, amount)
        obj.frequency = frequency
        return obj


def prompt_int(
    prompt: str,
    *,
    default: int | None = None,
    min_val: int | None = None,
    max_val: int | None = None,
    default_fmt: Callable = str,
    config_value: int | None = None,
) -> int:
    """Prompt user for an integer with validation and optional default.

    Note: unlike other prompt functions that receive the full ``config`` dict,
    this function takes a single *pre-extracted* value via ``config_value``.
    Callers extract the field from config before passing it in.
    """
    if config_value is True and default is not None:
        print(f"{prompt} [{default_fmt(default)}]: {default}")
        return default
    if config_value is not None:
        val = config_value
        prompt_suffix = f" [{default_fmt(default)}]:" if default is not None else ":"
        print(f"{prompt}{prompt_suffix} {val}")
        if min_val is not None and val < min_val:
            raise ValueError(f"{prompt}: config value {val} is below minimum {min_val}")
        if max_val is not None and val > max_val:
            raise ValueError(f"{prompt}: config value {val} is above maximum {max_val}")
        return val

    while True:
        display_prompt = (
            f"{prompt} [{default_fmt(default)}]: "
            if default is not None
            else f"{prompt}: "
        )
        user_input = input(display_prompt).strip()

        if not user_input and default is not None:
            return default

        try:
            val = int(user_input)
            if min_val is not None and val < min_val:
                print(f"Error: Value must be at least {min_val}.")
                continue
            if max_val is not None and val > max_val:
                print(f"Error: Value must be no more {max_val}.")
                continue
            return val
        except ValueError:
            print("Error: Please enter a whole number.")


def prompt_float(
    prompt: str,
    *,
    default: float | None = None,
    min_val: float | None = None,
    max_val: float | None = None,
    default_fmt: Callable = str,
    config_value: float | None = None,
) -> float:
    """Prompt user for a number with validation and optional default.

    Note: unlike other prompt functions that receive the full ``config`` dict,
    this function takes a single *pre-extracted* value via ``config_value``.
    Callers extract the field from config before passing it in.
    """
    if config_value is True and default is not None:
        print(f"{prompt} [{default_fmt(default)}]: {default}")
        return default
    if config_value is not None:
        val = float(config_value)
        prompt_suffix = f" [{default_fmt(default)}]:" if default is not None else ":"
        print(f"{prompt}{prompt_suffix} {val}")
        if min_val is not None and val < min_val:
            raise ValueError(f"{prompt}: config value {val} is below minimum {min_val}")
        if max_val is not None and val > max_val:
            raise ValueError(f"{prompt}: config value {val} is above maximum {max_val}")
        return val

    while True:
        display_prompt = (
            f"{prompt} [{default_fmt(default)}]: "
            if default is not None
            else f"{prompt}: "
        )
        user_input = input(display_prompt).strip()

        if not user_input and default is not None:
            return default

        try:
            val = float(user_input)
            if min_val is not None and val < min_val:
                print(f"Error: Value must be at least {min_val}.")
                continue
            if max_val is not None and val > max_val:
                print(f"Error: Value must be no more {max_val}.")
                continue
            return val
        except ValueError:
            print("Error: Please enter a number.")


def prompt_start_month(config: dict | None = None) -> int | None:
    """Prompt for contract start month. None means full tax year."""
    if config and "start_month" in config:
        val = config["start_month"]
        if val is True:
            print("Contract start month [1-12], ENTER for full year: full year")
            return None
        if val is not None:
            if not (1 <= val <= 12):
                raise ValueError(f"start_month: must be 1-12, got {val}")
            print(f"Contract start month [1-12], ENTER for full year: {val}")
            return val

    while True:
        user_input = input("Contract start month [1-12], ENTER for full year: ").strip()
        if not user_input:
            return None
        try:
            val = int(user_input)
            if 1 <= val <= 12:
                return val
        except ValueError:
            pass
        print("Error: Enter a number 1–12, or press ENTER for full year.")


def prompt_existing_income(
    start_month: int | None,
    config: dict | None = None,
) -> float:
    """Prompt for employment income already earned this tax year (partial year only)."""
    if config and "existing_income" in config:
        val = config["existing_income"]
        if val is True:
            print("Existing employment income already earned this tax year (£) [0]: 0")
            return 0.0
        if val is not None:
            print(
                f"Existing employment income already earned this tax year (£) [0]: {val}"
            )
            return float(val)
    if start_month is None:
        return 0.0
    return prompt_float(
        "Existing employment income already earned this tax year (£)",
        default=0,
        min_val=0,
    )


def prompt_existing_dividends(
    start_month: int | None,
    config: dict | None = None,
) -> float:
    """Prompt for dividends already received this tax year (partial year only)."""
    if config and "existing_dividends" in config:
        val = config["existing_dividends"]
        if val is True:
            print("Existing dividends already received this tax year (£) [0]: 0")
            return 0.0
        if val is not None:
            print(f"Existing dividends already received this tax year (£) [0]: {val}")
            return float(val)
    if start_month is None:
        return 0.0
    return prompt_float(
        "Existing dividends already received this tax year (£)",
        default=0,
        min_val=0,
    )


def prompt_existing_self_employment(
    start_month: int | None,
    config: dict | None = None,
) -> float:
    """Prompt for self-employment profit already earned this tax year (partial year only).

    For sole traders this consumes both Income Tax bands and Class 4 NI bands.
    See: https://www.gov.uk/self-employed-national-insurance-rates
    """
    if config and "existing_self_employment" in config:
        val = config["existing_self_employment"]
        if val is True:
            print(
                "Existing self-employment profit already earned this tax year (£) [0]: 0"
            )
            return 0.0
        if val is not None:
            print(
                f"Existing self-employment profit already earned this tax year (£) [0]: {val}"
            )
            return float(val)
    if start_month is None:
        return 0.0
    return prompt_float(
        "Existing self-employment profit already earned this tax year (£)",
        default=0,
        min_val=0,
    )


def _max_sacrifice(
    gross: int,
    mode: str,
    annual_margin: int = 0,
    admin_charge: int = 0,
) -> int:
    """Return the maximum feasible annual salary sacrifice for *mode*."""
    if mode == "paye":
        return min(gross, MAX_SALARY_SACRIFICE)
    if mode == "inside_ir35":
        max_within_budget = max(0, gross - annual_margin - admin_charge - 1)
        return min(max_within_budget, MAX_SALARY_SACRIFICE)
    return 0


def prompt_salary_sacrifice(
    gross: int,
    *,
    mode: str = "paye",
    start_month: int | None = None,
    working_days: int | None = None,
    annual_margin: int = 0,
    admin_charge: int = 0,
    is_paystream: bool = False,
    existing_income: float = 0,
    existing_dividends: float = 0,
    default_cap: int = 100_000,
    config: dict | None = None,
) -> SacrificeChoice:
    """Prompt whether to make a salary sacrifice for a personal pension.

    Returns a :class:`SacrificeChoice` (``int`` subclass) whose value is
    the *annual* sacrifice amount and whose ``.frequency`` is ``"monthly"``
    or ``"daily"``.

    *working_days* is required to convert a daily sacrifice to annual.
    In config mode the daily option is restricted to the PayStream
    umbrella; in manual mode daily is offered for any Inside IR35
    umbrella via an explicit monthly/daily choice.
    """
    if config:
        if not config.get("salary_sacrifice_enabled"):
            return SacrificeChoice(0, "monthly")

        contract_months = 12 if start_month is None else months_in_tax_year(start_month)

        ds = config.get("daily_salary_sacrifice")
        ms = config.get("monthly_salary_sacrifice")
        if ds is not None and ms is not None:
            raise ValueError(
                "set either 'monthly_salary_sacrifice' or "
                "'daily_salary_sacrifice', not both"
            )

        is_daily = ds is not None
        sac_val = ds if is_daily else ms
        label = "Daily" if is_daily else "Monthly"
        frequency: str = "daily" if is_daily else "monthly"
        per_period = working_days if is_daily else contract_months

        if is_daily and not is_paystream:
            raise ValueError(
                "'daily_salary_sacrifice' requires PayStream (is_paystream: true)"
            )

        if sac_val is True:
            sac_val = "auto"

        if isinstance(sac_val, int):
            if per_period is None:
                raise ValueError("daily_salary_sacrifice requires working days")
            annual = sac_val * per_period
            result = min(annual, MAX_SALARY_SACRIFICE)
            print(f"{label} salary sacrifice [ENTER=auto, or 'max'] (£): {sac_val}")
            return SacrificeChoice(result, frequency)

        if sac_val == "max":
            result = _max_sacrifice(gross, mode, annual_margin, admin_charge)
            print(f"{label} salary sacrifice [ENTER=auto, or 'max'] (£): max")
            return SacrificeChoice(result, frequency)

        if sac_val == "auto":
            raw_target = config.get("income_target")
            if raw_target is False:
                result = _max_sacrifice(gross, mode, annual_margin, admin_charge)
                print(f"{label} salary sacrifice [ENTER=auto, or 'max'] (£): auto")
                print("Income target: none (maxing pension)")
                return SacrificeChoice(result, frequency)
            if raw_target is None or raw_target is True:
                cap = prompt_int(
                    "Taxable income cap",
                    default=default_cap,
                    min_val=1,
                    default_fmt=format_gbp,
                )
            else:
                cap = raw_target
            if mode == "paye":
                result = calc_optimal_sacrifice_paye(gross, cap=cap)
            elif mode == "inside_ir35":
                result = calc_optimal_sacrifice_inside_ir35(
                    gross,
                    annual_margin,
                    cap=cap,
                    existing_income=existing_income,
                    existing_dividends=existing_dividends,
                    admin_charge=admin_charge,
                )
            else:
                result = 0
            if result == 0:
                print(
                    "Gross is already at or below cap — no sacrifice needed (payday.json)."
                )
                return SacrificeChoice(0, frequency)
            print(f"{label} salary sacrifice [ENTER=auto, or 'max'] (£): auto")
            print(f"Income target: {format_gbp(cap)}")
            return SacrificeChoice(result, frequency)

    answer = (
        input(
            "Would you like to make a salary sacrifice for a personal pension? [y/N]: "
        )
        .strip()
        .lower()
    )
    if answer != "y":
        return SacrificeChoice(0, "monthly")
    contract_months = 12 if start_month is None else months_in_tax_year(start_month)

    # Manual frequency choice — only for Inside IR35 (day-rate) mode.
    frequency = "monthly"
    if mode == "inside_ir35":
        while True:
            freq_input = (
                input("Salary sacrifice per day or per month? [m/d]: ").strip().lower()
            )
            if not freq_input or freq_input in ("m", "monthly", "month"):
                frequency = "monthly"
                break
            if freq_input in ("d", "daily", "day"):
                frequency = "daily"
                break
            print("Error: Enter 'm' for monthly or 'd' for daily.")
        if frequency == "daily" and working_days is None:
            raise ValueError("daily salary sacrifice requires working days")

    label = "Daily" if frequency == "daily" else "Monthly"

    while True:
        user_input = input(
            f"{label} salary sacrifice [ENTER=auto, or 'max'] (£): "
        ).strip()

        if not user_input:
            cap = prompt_int(
                "Taxable income cap",
                default=default_cap,
                min_val=1,
                default_fmt=format_gbp,
            )
            if mode == "paye":
                annual_sacrifice = calc_optimal_sacrifice_paye(gross, cap=cap)
            elif mode == "inside_ir35":
                annual_sacrifice = calc_optimal_sacrifice_inside_ir35(
                    gross,
                    annual_margin,
                    cap=cap,
                    existing_income=existing_income,
                    existing_dividends=existing_dividends,
                    admin_charge=admin_charge,
                )
            else:
                annual_sacrifice = 0

            if annual_sacrifice == 0:
                print(
                    "Your gross is already at or below the cap — no sacrifice needed."
                )
                return SacrificeChoice(0, frequency)

            # Warn only if the cap actually constrained the result.
            # PAYE: compare the unconstrained sacrifice against the limit.
            # Inside IR35: use equality as a proxy for capping — this may
            # produce a false positive if the optimal is exactly £60k.
            was_capped = (
                mode == "paye" and max(0, gross - cap) > MAX_SALARY_SACRIFICE
            ) or (mode == "inside_ir35" and annual_sacrifice == MAX_SALARY_SACRIFICE)
            if was_capped:
                print(f"Note: Salary sacrifice capped at £{MAX_SALARY_SACRIFICE:,}/yr.")

            if frequency == "daily" and working_days:
                per_day = annual_sacrifice // working_days
                print(
                    f"Auto-calculated: £{annual_sacrifice:,}/yr "
                    f"(£{per_day:,}/day) sacrifice."
                )
            else:
                monthly = annual_sacrifice // contract_months
                print(
                    f"Auto-calculated: £{annual_sacrifice:,}/yr "
                    f"(£{monthly:,}/mo) sacrifice."
                )
            print(f"Income target: {format_gbp(cap)}")
            return SacrificeChoice(annual_sacrifice, frequency)

        if user_input.lower() == "max":
            if mode == "paye":
                annual_sacrifice = min(gross, MAX_SALARY_SACRIFICE)
            elif mode == "inside_ir35":
                max_within_budget = max(0, gross - annual_margin - admin_charge - 1)
                annual_sacrifice = min(max_within_budget, MAX_SALARY_SACRIFICE)
            else:
                annual_sacrifice = 0

            if frequency == "daily" and working_days:
                per_day = annual_sacrifice // working_days
                print(
                    f"Maximum sacrifice: £{annual_sacrifice:,}/yr (£{per_day:,}/day)."
                )
            else:
                monthly = annual_sacrifice // contract_months
                print(f"Maximum sacrifice: £{annual_sacrifice:,}/yr (£{monthly:,}/mo).")
            return SacrificeChoice(annual_sacrifice, frequency)

        try:
            val = int(user_input)
            if val < 0:
                print("Error: Value must be at least 0.")
                continue
            if frequency == "daily":
                annual = val * working_days  # type: ignore[operator]
            else:
                annual = val * contract_months
            if annual > MAX_SALARY_SACRIFICE:
                if frequency == "daily" and working_days:
                    per_day_cap = MAX_SALARY_SACRIFICE // working_days
                    print(
                        f"Note: Salary sacrifice capped at £{MAX_SALARY_SACRIFICE:,}/yr "
                        f"(£{per_day_cap:,}/day)."
                    )
                else:
                    print(
                        f"Note: Salary sacrifice capped at £{MAX_SALARY_SACRIFICE:,}/yr "
                        f"(£{MAX_SALARY_SACRIFICE // contract_months:,}/mo)."
                    )
                annual = MAX_SALARY_SACRIFICE
            return SacrificeChoice(annual, frequency)
        except ValueError:
            print("Error: Please enter a whole number.")


def prompt_paystream(config: dict | None = None) -> bool:
    """Ask whether the umbrella company is PayStream. True = PayStream."""
    if config and config.get("is_paystream") is not None:
        val = config["is_paystream"]
        print(f"Is your umbrella company PayStream? [y/N]: {'yes' if val else 'no'}")
        return bool(val)
    answer = input("Is your umbrella company PayStream? [y/N]: ").strip().lower()
    return answer == "y"


def prompt_employment_allowance(config: dict | None = None) -> bool:
    """Ask whether the company can claim Employment Allowance.

    Single-director companies (sole director as only employee) cannot claim.
    See https://www.gov.uk/claim-employment-allowance and
    https://www.gov.uk/government/publications/employment-allowance-more-detailed-guidance/single-director-companies-and-employment-allowance-further-employer-guidance
    """
    if config and config.get("employment_allowance") is not None:
        val = config["employment_allowance"]
        print(
            f"Can your company claim Employment Allowance? [y/N]: {'yes' if val else 'no'}"
        )
        return bool(val)
    answer = (
        input(
            "Can your company claim Employment Allowance? (single-director companies cannot) [y/N]: "
        )
        .strip()
        .lower()
    )
    return answer == "y"


def prompt_region(config: dict | None = None) -> str:
    """Ask whether the taxpayer is a Scottish taxpayer.

    Returns ``"scotland"`` or ``"rest_of_uk"`` (aliases ``england``/``wales``/
    ``northern_ireland`` normalise to rest_of_uk).

    When *config* is provided (config-file mode) and ``region`` is absent
    (``None``), defaults to ``rest_of_uk`` without prompting — mirroring
    that England/Wales/NI share one rate set.
    """
    if config is not None:
        val = config.get("region")
        if val is not None:
            print(
                f"Is your tax region Scotland? [y/N]: {'yes' if val == 'scotland' else 'no'}"
            )
            return "scotland" if val == "scotland" else "rest_of_uk"
        return "rest_of_uk"
    answer = input("Is your tax region Scotland? [y/N]: ").strip().lower()
    return "scotland" if answer == "y" else "rest_of_uk"


def prompt_student_loan(
    config: dict | None = None,
) -> tuple[str | None, bool]:
    """Prompt for student loan plan and postgraduate loan.

    Returns (student_loan_plan, postgraduate_loan) where plan is one of
    ``"plan1"/"plan2"/"plan4"/"plan5"`` or ``None``, and postgraduate is a bool.

    In config mode absent/null means no loan (no prompt, no repayment).
    The undergraduate plan and postgraduate loan stack independently — a
    borrower can hold both at once.
    """
    if config is not None:
        plan = config.get("student_loan_plan")
        pgl = bool(config.get("postgraduate_loan"))
        if plan:
            print(f"Student loan plan: {plan}")
        else:
            print("Student loan plan: none")
        print(f"Postgraduate loan: {'yes' if pgl else 'no'}")
        return plan, pgl

    # Interactive: undergraduate plan
    plan: str | None = None
    while True:
        raw = input("Student loan plan [1/2/4/5, ENTER for none]: ").strip().lower()
        if not raw:
            plan = None
            break
        # Accept "1", "plan1", "plan 1", etc.
        normalised = raw.replace(" ", "").replace("plan", "")
        if normalised in ("1", "2", "4", "5"):
            plan = f"plan{normalised}"
            break
        print("Error: Enter 1, 2, 4, 5, or press ENTER for none.")

    pgl_answer = input("Do you have a Postgraduate Loan? [y/N]: ").strip().lower()
    has_pgl = pgl_answer == "y"
    return plan, has_pgl


def _resolve_days_off(config: dict, default: int = 25) -> int:
    """Extract days_off from config, using ``default`` when True or absent."""
    raw = config.get("days_off")
    return default if raw is True or raw is None else raw


def prompt_working_days(
    start_month: int | None,
    config: dict | None = None,
) -> tuple[int, int]:
    """Prompt for working days with holiday-aware defaults and manual override.

    Returns (net_working_days, days_off_taken).
    """
    if start_month is None:
        available = working_days_in_full_tax_year()
        period = "2026/27"
    else:
        available = working_days_in_contract_period(start_month)
        period = contract_period_label(start_month, months_in_tax_year(start_month))

    print(
        f"Working days available in {period} "
        f"(Mon–Fri minus E&W bank holidays): {available}"
    )

    if config and config.get("working_days") is True:
        days_off = _resolve_days_off(config)
        net = max(1, available - days_off)
        print(f"Days off you'll take (annual leave, sick, etc.) [25]: {days_off}")
        return net, days_off

    if config and config.get("working_days") is not None:
        net = config["working_days"]
        days_off = _resolve_days_off(config)
        print(
            f"Press ENTER to accept {net} working days, or type a custom value: {net}"
        )
        return net, days_off

    if config and config.get("days_off") is True:
        days_off = 25
        print(f"Days off you'll take (annual leave, sick, etc.) [25]: {days_off}")
        net = max(1, available - days_off)
        return net, days_off

    if config and config.get("days_off") is not None:
        days_off = config["days_off"]
        print(f"Days off you'll take (annual leave, sick, etc.) [25]: {days_off}")
        net = max(1, available - days_off)
        return net, days_off

    days_off = prompt_int(
        "Days off you'll take (annual leave, sick, etc.)",
        default=25,
        min_val=0,
    )

    net = max(1, available - days_off)

    while True:
        user_input = input(
            f"Press ENTER to accept {net} working days, or type a custom value: "
        ).strip()
        if not user_input:
            return net, days_off
        try:
            val = int(user_input)
            if val < 1:
                print("Error: Value must be at least 1.")
                continue
            if val > 365:
                print("Error: Value must be no more 365.")
                continue
            return val, days_off
        except ValueError:
            print("Error: Please enter a whole number.")


def select_mode(config: dict | None = None) -> int:
    """Display mode menu and return 1, 2, 3, or 4."""
    if config and config.get("mode") is not None:
        raw = config["mode"]
        if isinstance(raw, str):
            mode = VALID_MODES[raw]
        else:
            mode = raw
        print(f"\nChoice [1/2/3/4]: {mode}")
        return mode

    print("\n╔═══════════════════════════════════════╗")
    print("║      Payday - UK Salary Calculator    ║")
    print("║            2026/27 Tax Year           ║")
    print("╚═══════════════════════════════════════╝")
    print("\nSelect calculation mode:")
    print("  [1] Regular PAYE")
    print("  [2] Inside IR35 (Umbrella)")
    print("  [3] Outside IR35 (Ltd Co)")
    print("  [4] Sole Trader (Self-Employed)")

    return prompt_int("\nChoice [1/2/3/4]", min_val=1, max_val=4)


def run_once(config: dict | None = None) -> None:
    """One full cycle: select mode → prompt → calculate → display."""
    mode = select_mode(config)

    if mode == 1:
        print("\n═══════════════════════════════════════")
        print("  Regular PAYE")
        print("═══════════════════════════════════════")
        region = prompt_region(config)
        salary = prompt_int(
            "Enter your annual gross salary (£)",
            min_val=0,
            config_value=config.get("salary") if config else None,
        )
        salary_sacrifice = prompt_salary_sacrifice(salary, mode="paye", config=config)
        student_loan_plan, postgraduate_loan = prompt_student_loan(config)
        breakdown = PAYECalculator.calculate(
            salary,
            salary_sacrifice=int(salary_sacrifice),
            region=region,
            student_loan_plan=student_loan_plan,
            postgraduate_loan=postgraduate_loan,
        )

    elif mode == 2:
        print("\n═══════════════════════════════════════")
        print("  Inside IR35 (Umbrella Company)")
        print("═══════════════════════════════════════")
        day_rate = prompt_int(
            "Enter your day rate (£)",
            min_val=1,
            config_value=config.get("day_rate") if config else None,
        )
        start_month = prompt_start_month(config)
        existing_income = prompt_existing_income(start_month, config)
        existing_dividends = prompt_existing_dividends(start_month, config)

        net_working_days, _ = prompt_working_days(start_month, config)
        margin = prompt_int(
            "Umbrella weekly margin (£)",
            default=25,
            min_val=0,
            config_value=config.get("umbrella_margin") if config else None,
        )
        is_paystream = prompt_paystream(config)
        region = prompt_region(config)
        student_loan_plan, postgraduate_loan = prompt_student_loan(config)

        weeks = net_working_days / 5
        annual_margin = round(margin * weeks)

        annual_assignment = day_rate * net_working_days

        annual_admin_charge = (
            round(PAYSTREAM_ADMIN_CHARGE_WEEKLY * weeks) if is_paystream else 0
        )

        sacrifice_choice = prompt_salary_sacrifice(
            annual_assignment,
            mode="inside_ir35",
            start_month=start_month,
            working_days=net_working_days,
            annual_margin=annual_margin,
            admin_charge=annual_admin_charge,
            is_paystream=is_paystream,
            existing_income=existing_income,
            existing_dividends=existing_dividends,
            config=config,
        )
        breakdown = InsideIR35Calculator.calculate(
            day_rate,
            net_working_days,
            margin,
            start_month,
            existing_income,
            existing_dividends=existing_dividends,
            salary_sacrifice=int(sacrifice_choice),
            is_paystream=is_paystream,
            sacrifice_frequency=getattr(sacrifice_choice, "frequency", "monthly"),
            effective_days=net_working_days,
            region=region,
            student_loan_plan=student_loan_plan,
            postgraduate_loan=postgraduate_loan,
        )

    elif mode == 3:
        print("\n═══════════════════════════════════════")
        print("  Outside IR35 (Limited Company)")
        print("═══════════════════════════════════════")
        day_rate = prompt_int(
            "Enter your day rate (£)",
            min_val=1,
            config_value=config.get("day_rate") if config else None,
        )
        start_month = prompt_start_month(config)
        existing_income = prompt_existing_income(start_month, config)
        existing_dividends = prompt_existing_dividends(start_month, config)

        net_working_days, _ = prompt_working_days(start_month, config)

        region = prompt_region(config)
        director_salary = prompt_int(
            "Director salary (£)",
            default=12_570,
            min_val=0,
            config_value=config.get("director_salary") if config else None,
        )
        company_expenses = prompt_int(
            "Annual company expenses (accountancy, insurance, etc.) (£)",
            default=0,
            min_val=0,
            config_value=config.get("company_expenses") if config else None,
        )
        director_pension = prompt_int(
            "Director pension contribution (£)",
            default=0,
            min_val=0,
            max_val=MAX_SALARY_SACRIFICE,
            config_value=config.get("director_pension") if config else None,
        )
        retained_profit = prompt_int(
            "Profit retained in company (£)",
            default=0,
            min_val=0,
            config_value=config.get("retained_profit") if config else None,
        )
        employment_allowance = prompt_employment_allowance(config)
        student_loan_plan, postgraduate_loan = prompt_student_loan(config)

        breakdown = OutsideIR35Calculator.calculate(
            day_rate,
            net_working_days,
            start_month,
            existing_income,
            existing_dividends=existing_dividends,
            effective_days=net_working_days,
            director_salary=director_salary,
            director_pension=director_pension,
            company_expenses=company_expenses,
            retained_profit=retained_profit,
            employment_allowance=employment_allowance,
            region=region,
            student_loan_plan=student_loan_plan,
            postgraduate_loan=postgraduate_loan,
        )

    elif mode == 4:
        print("\n═══════════════════════════════════════")
        print("  Sole Trader (Self-Employed)")
        print("═══════════════════════════════════════")
        day_rate = prompt_int(
            "Enter your day rate (£)",
            min_val=1,
            config_value=config.get("day_rate") if config else None,
        )
        start_month = prompt_start_month(config)
        existing_income = prompt_existing_income(start_month, config)
        existing_self_employment = prompt_existing_self_employment(start_month, config)

        net_working_days, _ = prompt_working_days(start_month, config)

        business_expenses = prompt_int(
            "Annual business expenses (£)",
            default=0,
            min_val=0,
            config_value=config.get("business_expenses") if config else None,
        )
        personal_pension = prompt_int(
            "Personal pension contribution (£)",
            default=0,
            min_val=0,
            max_val=MAX_SALARY_SACRIFICE,
            config_value=config.get("personal_pension") if config else None,
        )
        region = prompt_region(config)
        student_loan_plan, postgraduate_loan = prompt_student_loan(config)

        breakdown = SoleTraderCalculator.calculate(
            day_rate,
            net_working_days,
            start_month,
            existing_income,
            existing_self_employment=existing_self_employment,
            business_expenses=business_expenses,
            personal_pension=personal_pension,
            effective_days=net_working_days,
            region=region,
            student_loan_plan=student_loan_plan,
            postgraduate_loan=postgraduate_loan,
        )

    else:
        return

    print("\n" + format_breakdown(breakdown))


def main(config: dict | None = None) -> None:
    """Main entry point. Loops run_once() until user quits."""
    try:
        while True:
            run_once(config)
            again = input("\nRun another calculation? [y/N]: ").strip().lower()
            if again != "y":
                print("Goodbye!")
                break
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
