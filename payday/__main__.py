import argparse
import sys
from payday.cli import main as payday_main
from payday.config import load_config, generate_template


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
        cfg = load_config(args.config)
        if cfg is None:
            print(f"Config file not found: {args.config}")
            sys.exit(1)
        config = cfg

    payday_main(config)
