"""
Command-line interface & scheduler — the "automate" stage.

This is the front door of CryptoPulse. Running `python -m cryptopulse` executes
this file. It exposes three subcommands:

    run-once   Run a single full pipeline cycle and exit.
    run        Run a cycle now, then repeat it every N minutes (the scheduler).
    status     Print a quick summary of what's currently stored.

We use argparse (standard library) to parse arguments and the `schedule`
library for the repeating timer. A scheduler turns a script you run by hand into
an automation that runs itself — the whole point of the project.

Why a CLI? It gives the project a clean, documented, professional interface that
you can demo, screenshot, and that a server's cron/Task Scheduler can call.
"""

from __future__ import annotations

import argparse
import time

import schedule

from .analysis import summarise_all
from .config import load_settings
from .logging_setup import get_logger
from .pipeline import run_cycle
from .storage import PriceStore

log = get_logger("cryptopulse.cli")


def _print_cycle(result) -> None:
    """Pretty-print the outcome of a single cycle to the console."""
    print(f"  fetched : {result.fetched}")
    print(f"  stored  : {result.stored}")
    print(f"  alerts  : {len(result.alerts)}")
    for alert in result.alerts:
        print(f"      🚨 {alert.describe()}")
    print(f"  dashboard: {result.dashboard_path}")


def cmd_run_once(_args: argparse.Namespace) -> None:
    """Run exactly one pipeline cycle."""
    settings = load_settings()
    print(f"Running one cycle for: {', '.join(settings.coins)}")
    result = run_cycle(settings)
    _print_cycle(result)


def cmd_run(args: argparse.Namespace) -> None:
    """Run a cycle immediately, then on a repeating schedule until stopped."""
    settings = load_settings()
    interval = max(1, args.interval)  # never allow an interval below 1 minute

    print(f"Starting CryptoPulse scheduler — every {interval} minute(s).")
    print("Press Ctrl+C to stop.\n")

    # Run once right away so you don't wait a full interval for the first cycle.
    _print_cycle(run_cycle(settings))

    # Then schedule the repeat. schedule.every(...).do(...) registers the job;
    # run_pending() fires it when due. We sleep between checks to stay idle.
    schedule.every(interval).minutes.do(lambda: _print_cycle(run_cycle(settings)))

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nScheduler stopped. Goodbye.")


def cmd_status(_args: argparse.Namespace) -> None:
    """Print a quick status report from whatever is already stored."""
    settings = load_settings()
    store = PriceStore()
    total = store.row_count()
    print(f"Database holds {total} snapshot(s).")
    print(f"Email alerts: {'ENABLED' if settings.email_enabled else 'disabled (configure .env)'}")

    summaries = summarise_all(settings.coins, store)
    if not summaries:
        print("No coin history yet. Run 'python -m cryptopulse run-once' to collect data.")
        return

    print("\nCurrent snapshot:")
    for s in summaries:
        change = f"{s.change_24h:+.2f}%" if s.change_24h is not None else "n/a"
        print(f"  {s.coin:>10} | {s.latest_price:>12,.2f} | trend {s.trend:<4} | 24h {change}")


def build_parser() -> argparse.ArgumentParser:
    """Define the CLI: the program name, help text, and subcommands."""
    parser = argparse.ArgumentParser(
        prog="cryptopulse",
        description="Automated crypto market tracker, analyzer, and alerter.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("run-once", help="Run a single pipeline cycle and exit.")

    run_p = sub.add_parser("run", help="Run continuously on a schedule.")
    run_p.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Minutes between cycles (default: 10).",
    )

    sub.add_parser("status", help="Show a summary of stored data.")
    return parser


def main(argv: list[str] | None = None) -> None:
    """Parse arguments and dispatch to the chosen subcommand."""
    parser = build_parser()
    args = parser.parse_args(argv)

    handlers = {
        "run-once": cmd_run_once,
        "run": cmd_run,
        "status": cmd_status,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
