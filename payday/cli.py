import sys
from payday.config import VALID_MODES
from payday.constants import MAX_SALARY_SACRIFICE
from payday.calculators.optimal_sacrifice import (
    calc_optimal_sacrifice_inside_ir35,
    calc_optimal_sacrifice_paye,
)
from payday.calculators.paye import PAYECalculator
from payday.calculators.inside_ir35 import InsideIR35Calculator
from payday.calculators.outside_ir35 import OutsideIR35Calculator
from payday.formatters import format_breakdown, format_gbp
from payday.tax_year import (
    contract_period_label,
    months_in_tax_year,
    working_days_in_contract_period,
    working_days_in_full_tax_year,
)


def prompt_int(
    prompt: str,
    *,
    default: int | None = None,
    min_val: int | None = None,
    max_val: int | None = None,
    default_fmt: callable = str,
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
    default_fmt: callable = str,
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
            print(f"Existing employment income already earned this tax year (£) [0]: {val}")
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


def prompt_salary_sacrifice(
    gross: int,
    *,
    mode: str = "paye",
    start_month: int | None = None,
    annual_margin: int = 0,
    existing_income: float = 0,
    existing_dividends: float = 0,
    default_cap: int = 100_000,
    config: dict | None = None,
) -> int:
    """Prompt whether to make a salary sacrifice for a personal pension.

    Returns the *annual* sacrifice amount.
    """
    if config:
        if not config.get("salary_sacrifice_enabled"):
            return 0

        contract_months = 12 if start_month is None else months_in_tax_year(start_month)

        ms = config.get("monthly_salary_sacrifice")
        if ms is True:
            ms = "auto"

        if isinstance(ms, int):
            annual = ms * contract_months
            result = min(annual, MAX_SALARY_SACRIFICE)
            print(f"Monthly salary sacrifice [ENTER=auto, or 'max'] (£): {ms}")
            return result

        if ms == "max":
            if mode == "paye":
                result = min(gross, MAX_SALARY_SACRIFICE)
            elif mode == "inside_ir35":
                max_within_budget = max(0, gross - annual_margin - 1)
                result = min(max_within_budget, MAX_SALARY_SACRIFICE)
            else:
                result = 0
            monthly = result // contract_months
            print(f"Monthly salary sacrifice [ENTER=auto, or 'max'] (£): max")
            return result

        if ms == "auto":
            raw_target = config.get("income_target")
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
                    gross, annual_margin, cap=cap,
                    existing_income=existing_income,
                    existing_dividends=existing_dividends,
                )
            else:
                result = 0
            if result == 0:
                print("Gross is already at or below cap — no sacrifice needed (payday.json).")
                return 0
            print(f"Monthly salary sacrifice [ENTER=auto, or 'max'] (£): auto")
            return result

    answer = (
        input(
            "Would you like to make a salary sacrifice for a personal pension? [y/N]: "
        )
        .strip()
        .lower()
    )
    if answer != "y":
        return 0
    contract_months = 12 if start_month is None else months_in_tax_year(start_month)

    while True:
        user_input = input("Monthly salary sacrifice [ENTER=auto, or 'max'] (£): ").strip()

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
                )
            else:
                annual_sacrifice = 0

            if annual_sacrifice == 0:
                print(
                    "Your gross is already at or below the cap — no sacrifice needed."
                )
                return 0

            # Warn only if the cap actually constrained the result.
            # PAYE: compare the unconstrained sacrifice against the limit.
            # Inside IR35: use equality as a proxy for capping — this may
            # produce a false positive if the optimal is exactly £60k.
            was_capped = (
                mode == "paye" and max(0, gross - cap) > MAX_SALARY_SACRIFICE
            ) or (mode == "inside_ir35" and annual_sacrifice == MAX_SALARY_SACRIFICE)
            if was_capped:
                print(f"Note: Salary sacrifice capped at £{MAX_SALARY_SACRIFICE:,}/yr.")

            monthly = annual_sacrifice // contract_months
            print(
                f"Auto-calculated: £{annual_sacrifice:,}/yr "
                f"(£{monthly:,}/mo) sacrifice."
            )
            return annual_sacrifice

        if user_input.lower() == "max":
            if mode == "paye":
                annual_sacrifice = min(gross, MAX_SALARY_SACRIFICE)
            elif mode == "inside_ir35":
                max_within_budget = max(0, gross - annual_margin - 1)
                annual_sacrifice = min(max_within_budget, MAX_SALARY_SACRIFICE)
            else:
                annual_sacrifice = 0

            monthly = annual_sacrifice // contract_months
            print(
                f"Maximum sacrifice: £{annual_sacrifice:,}/yr "
                f"(£{monthly:,}/mo)."
            )
            return annual_sacrifice

        try:
            val = int(user_input)
            if val < 0:
                print("Error: Value must be at least 0.")
                continue
            annual = val * contract_months
            if annual > MAX_SALARY_SACRIFICE:
                print(
                    f"Note: Salary sacrifice capped at £{MAX_SALARY_SACRIFICE:,}/yr "
                    f"(£{MAX_SALARY_SACRIFICE // contract_months:,}/mo)."
                )
                annual = MAX_SALARY_SACRIFICE
            return annual
        except ValueError:
            print("Error: Please enter a whole number.")


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
        print(f"Press ENTER to accept {net} working days, or type a custom value: {net}")
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
    """Display mode menu and return 1, 2, or 3."""
    if config and config.get("mode") is not None:
        raw = config["mode"]
        if isinstance(raw, str):
            mode = VALID_MODES[raw]
        else:
            mode = raw
        print(f"\nChoice [1/2/3]: {mode}")
        return mode

    print("\n╔═══════════════════════════════════════╗")
    print("║      Payday - UK Salary Calculator    ║")
    print("║            2026/27 Tax Year           ║")
    print("╚═══════════════════════════════════════╝")
    print("\nSelect calculation mode:")
    print("  [1] Regular PAYE")
    print("  [2] Inside IR35 (Umbrella)")
    print("  [3] Outside IR35 (Ltd Co)")

    return prompt_int("\nChoice [1/2/3]", min_val=1, max_val=3)


def run_once(config: dict | None = None) -> None:
    """One full cycle: select mode → prompt → calculate → display."""
    mode = select_mode(config)

    if mode == 1:
        print("\n═══════════════════════════════════════")
        print("  Regular PAYE")
        print("═══════════════════════════════════════")
        salary = prompt_int(
            "Enter your annual gross salary (£)", min_val=0,
            config_value=config.get("salary") if config else None,
        )
        salary_sacrifice = prompt_salary_sacrifice(salary, mode="paye", config=config)
        breakdown = PAYECalculator.calculate(salary, salary_sacrifice=salary_sacrifice)

    elif mode == 2:
        print("\n═══════════════════════════════════════")
        print("  Inside IR35 (Umbrella Company)")
        print("═══════════════════════════════════════")
        day_rate = prompt_int(
            "Enter your day rate (£)", min_val=1,
            config_value=config.get("day_rate") if config else None,
        )
        start_month = prompt_start_month(config)
        existing_income = prompt_existing_income(start_month, config)
        existing_dividends = prompt_existing_dividends(start_month, config)

        net_working_days, _ = prompt_working_days(start_month, config)
        margin = prompt_int(
            "Umbrella weekly margin (£)", default=25, min_val=0,
            config_value=config.get("umbrella_margin") if config else None,
        )

        weeks = net_working_days / 5
        annual_margin = round(margin * weeks)

        annual_assignment = day_rate * net_working_days

        salary_sacrifice = prompt_salary_sacrifice(
            annual_assignment,
            mode="inside_ir35",
            start_month=start_month,
            annual_margin=annual_margin,
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
            salary_sacrifice=salary_sacrifice,
            effective_days=net_working_days,
        )

    elif mode == 3:
        print("\n═══════════════════════════════════════")
        print("  Outside IR35 (Limited Company)")
        print("═══════════════════════════════════════")
        day_rate = prompt_int(
            "Enter your day rate (£)", min_val=1,
            config_value=config.get("day_rate") if config else None,
        )
        start_month = prompt_start_month(config)
        existing_income = prompt_existing_income(start_month, config)
        existing_dividends = prompt_existing_dividends(start_month, config)

        net_working_days, _ = prompt_working_days(start_month, config)

        breakdown = OutsideIR35Calculator.calculate(
            day_rate,
            net_working_days,
            start_month,
            existing_income,
            existing_dividends=existing_dividends,
            effective_days=net_working_days,
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
