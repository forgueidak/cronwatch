import subprocess
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class JobResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    started_at: float
    success: bool = field(init=False)

    def __post_init__(self):
        self.success = self.exit_code == 0

    def summary(self) -> str:
        status = "SUCCESS" if self.success else "FAILURE"
        return (
            f"[{status}] command={self.command!r} "
            f"exit_code={self.exit_code} "
            f"duration={self.duration_seconds:.2f}s"
        )


def run_job(
    command: str,
    timeout: Optional[int] = None,
    shell: bool = True,
) -> JobResult:
    """Execute a shell command and return a JobResult."""
    logger.info("Starting job: %s", command)
    started_at = time.time()

    try:
        proc = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = time.time() - started_at
        result = JobResult(
            command=command,
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            duration_seconds=duration,
            started_at=started_at,
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.time() - started_at
        logger.error("Job timed out after %s seconds: %s", timeout, command)
        result = JobResult(
            command=command,
            exit_code=-1,
            stdout=exc.stdout or "",
            stderr=f"TimeoutExpired: job exceeded {timeout}s",
            duration_seconds=duration,
            started_at=started_at,
        )

    logger.info(result.summary())
    return result
