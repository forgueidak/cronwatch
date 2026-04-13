import sys
import argparse
import logging

from cronwatch.config import load_config
from cronwatch.runner import run_job
from cronwatch.logger import setup_logging, write_job_log

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatch",
        description="Monitor and log cron job execution with alerting.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to execute and monitor.",
    )
    parser.add_argument(
        "-c", "--config",
        default="cronwatch.yaml",
        help="Path to cronwatch config file (default: cronwatch.yaml).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Timeout in seconds for the command.",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Override log level (DEBUG, INFO, WARNING, ERROR).",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_config(args.config)
    log_level = args.log_level or config.log_level
    setup_logging(level=log_level, log_file=config.log_file)

    if not args.command:
        parser.print_help()
        return 1

    command = " ".join(args.command)
    timeout = args.timeout or config.timeout

    result = run_job(command, timeout=timeout)
    write_job_log(result, log_dir=config.log_dir)

    if not result.success:
        logger.warning("Job failed: %s", result.summary())
        return result.exit_code if result.exit_code > 0 else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
