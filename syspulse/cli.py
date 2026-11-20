"""Command-line entrypoint for SysPulse."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time

from rich.console import Console
from rich.live import Live

from . import __version__
from .metrics import MetricsCollector
from .ui import DashboardRenderer


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="syspulse",
        description="SysPulse — Zero-bloat terminal system monitor and telemetry dashboard.",
    )
    parser.add_argument(
        "-r",
        "--refresh",
        type=float,
        default=1.0,
        help="Refresh interval in seconds (default: 1.0, minimum: 0.2)",
    )
    parser.add_argument(
        "-s",
        "--sort",
        choices=["cpu", "mem"],
        default="cpu",
        help="Sort top processes by 'cpu' or 'mem' usage (default: cpu)",
    )
    parser.add_argument(
        "-n",
        "--procs",
        type=int,
        default=8,
        help="Number of top processes to display (default: 8)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Render a single frame and exit immediately",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output a single system telemetry snapshot as formatted JSON and exit",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    refresh = max(0.2, args.refresh)
    proc_limit = max(1, min(50, args.procs))

    collector = MetricsCollector()
    # Brief warm-up interval so initial process/CPU deltas are accurate
    time.sleep(0.15)

    if args.json:
        snapshot = collector.collect(process_limit=proc_limit, sort_by=args.sort)
        print(json.dumps(dataclasses.asdict(snapshot), indent=2))
        return 0

    console = Console()
    renderer = DashboardRenderer()

    if args.once:
        snapshot = collector.collect(process_limit=proc_limit, sort_by=args.sort)
        console.print(renderer.render(snapshot, refresh, args.sort))
        return 0

    try:
        with Live(
            renderer.render(
                collector.collect(process_limit=proc_limit, sort_by=args.sort),
                refresh,
                args.sort,
            ),
            console=console,
            screen=True,
            refresh_per_second=max(1, int(round(1.0 / refresh))),
        ) as live:
            while True:
                time.sleep(refresh)
                snapshot = collector.collect(process_limit=proc_limit, sort_by=args.sort)
                live.update(renderer.render(snapshot, refresh, args.sort))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
