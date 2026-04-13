import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cronwatch.runner import JobResult


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Configure root logger for cronwatch."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


def write_job_log(result: JobResult, log_dir: str = "/var/log/cronwatch") -> str:
    """Append a JSON log entry for a job result. Returns the log file path."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_path = os.path.join(log_dir, "jobs.jsonl")

    entry = {
        "timestamp": datetime.fromtimestamp(result.started_at, tz=timezone.utc).isoformat(),
        "command": result.command,
        "exit_code": result.exit_code,
        "success": result.success,
        "duration_seconds": round(result.duration_seconds, 4),
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }

    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")

    return log_path
