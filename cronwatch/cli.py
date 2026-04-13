"""CLI entry point for cronwatch."""

from __future__ import annotations

import argparse
import sys

from cronwatch.config import load_config
from cronwatch.digest import build_digest, format_digest_text
from cronwatch.watcher import watch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatch",
        description="Monitor, log, and alert on cron job failures.",
    )
    parser.add_argument(
        "--config", default="cronwatch.yaml", metavar="FILE",
        help="Path to YAML config file (default: cronwatch.yaml)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # run sub-command
    run_p = sub.add_parser("run", help="Run and monitor a single command.")
    run_p.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to execute")
    run_p.add_argument("--timeout", type=int, default=None, help="Timeout in seconds")
    run_p.add_argument(
        "--notify-on-success", action="store_true",
        help="Send notifications even on success",
    )

    # digest sub-command
    digest_p = sub.add_parser("digest", help="Print a digest report of recent job history.")
    digest_p.add_argument(
        "jobs", nargs="+", metavar="CMD",
        help="One or more job command strings to include in the digest",
    )
    digest_p.add_argument(
        "--limit", type=int, default=50,
        help="Maximum history entries per job (default: 50)",
    )
    digest_p.add_argument(
        "--log-dir", default="/var/log/cronwatch",
        help="Directory where job logs are stored",
    )

    return parser


def main(argv: list[str] | None = None) -> int:  # pragma: no cover
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg = load_config(args.config)

    if args.command == "run":
        cmd = " ".join(args.cmd)
        if not cmd:
            parser.error("No command provided to 'run'.")
        watch(
            command=cmd,
            config=cfg,
            timeout=args.timeout,
            notify_on_success=args.notify_on_success,
        )
        return 0

    if args.command == "digest":
        entries = build_digest(
            commands=args.jobs,
            log_dir=args.log_dir,
            limit=args.limit,
        )
        print(format_digest_text(entries))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
