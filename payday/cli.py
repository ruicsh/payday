import sys
from payday.calculators.paye import PAYECalculator
from payday.calculators.inside_ir35 import InsideIR35Calculator
from payday.calculators.outside_ir35 import OutsideIR35Calculator
from payday.formatters import format_breakdown


def prompt_int(
    prompt: str,
    *,
    default: int | None = None,
    min_val: int | None = None,
    max_val: int | None = None,
) -> int:
    """Prompt user for an integer with validation and optional default."""
    while True:
        display_prompt = (
            f"{prompt} [{default}]: " if default is not None else f"{prompt}: "
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


def select_mode() -> int:
    """Display mode menu and return 1, 2, or 3."""
    print("\n╔═══════════════════════════════════════╗")
    print("║      Payday - UK Salary Calculator    ║")
    print("║            2026/27 Tax Year           ║")
    print("╚═══════════════════════════════════════╝")
    print("\nSelect calculation mode:")
    print("  [1] Regular PAYE")
    print("  [2] Inside IR35 (Umbrella)")
    print("  [3] Outside IR35 (Ltd Co)")

    return prompt_int("\nChoice [1/2/3]", min_val=1, max_val=3)


def run_once() -> None:
    """One full cycle: select mode → prompt → calculate → display."""
    mode = select_mode()

    if mode == 1:
        print("\n═══════════════════════════════════════")
        print("  Regular PAYE")
        print("═══════════════════════════════════════")
        salary = prompt_int("Enter your annual gross salary (£)", min_val=0)
        breakdown = PAYECalculator.calculate(salary)

    elif mode == 2:
        print("\n═══════════════════════════════════════")
        print("  Inside IR35 (Umbrella Company)")
        print("═══════════════════════════════════════")
        day_rate = prompt_int("Enter your day rate (£)", min_val=1)
        working_days = prompt_int(
            "Working days per year", default=240, min_val=1, max_val=365
        )
        margin = prompt_int("Umbrella weekly margin (£)", default=25, min_val=0)
        breakdown = InsideIR35Calculator.calculate(day_rate, working_days, margin)

    elif mode == 3:
        print("\n═══════════════════════════════════════")
        print("  Outside IR35 (Limited Company)")
        print("═══════════════════════════════════════")
        day_rate = prompt_int("Enter your day rate (£)", min_val=1)
        working_days = prompt_int(
            "Working days per year", default=240, min_val=1, max_val=365
        )
        breakdown = OutsideIR35Calculator.calculate(day_rate, working_days)

    else:
        return

    print("\n" + format_breakdown(breakdown))


def main() -> None:
    """Main entry point. Loops run_once() until user quits."""
    try:
        while True:
            run_once()
            again = input("\nRun another calculation? [y/N]: ").strip().lower()
            if again != "y":
                print("Goodbye!")
                break
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
