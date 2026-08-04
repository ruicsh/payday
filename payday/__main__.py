import argparse
import sys
from pathlib import Path
from payday.cli import main as payday_main
from payday.config import load_config, generate_template

CONTRACTS_DIR = Path("contracts")


def list_contracts() -> list[Path]:
    if not CONTRACTS_DIR.is_dir():
        return []
    return sorted(CONTRACTS_DIR.glob("*.json"))


def select_contract() -> dict | None:
    contracts = list_contracts()
    if not contracts:
        return None

    print("Contracts:")
    for i, path in enumerate(contracts, start=1):
        print(f"  [{i}] {path.stem}")
    print("  [0] Manual entry")

    while True:
        raw = input(f"\nSelect a contract [0-{len(contracts)}]: ").strip()
        if raw == "":
            return None
        try:
            choice = int(raw)
        except ValueError:
            print(f"Invalid choice: {raw}")
            continue
        if choice == 0:
            return None
        if 1 <= choice <= len(contracts):
            try:
                return load_config(str(contracts[choice - 1]))
            except ValueError as e:
                print(f"Error: {e}")
                sys.exit(1)
        print(f"Invalid choice: {raw}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Payday - UK Salary Calculator 2026/27"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to payday.json config file",
    )
    parser.add_argument(
        "--init",
        nargs="?",
        const="payday.json",
        default=None,
        help="Generate a template config file [default: payday.json]",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()

    if args.init:
        generate_template(args.init)
        sys.exit(0)

    config = None
    if args.config:
        try:
            cfg = load_config(args.config)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        if cfg is None:
            print(f"Config file not found: {args.config}")
            config = select_contract()
        else:
            config = cfg
    else:
        config = select_contract()

    payday_main(config)
