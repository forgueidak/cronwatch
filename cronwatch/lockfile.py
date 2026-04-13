"""Lockfile support to prevent concurrent execution of the same cron job."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

_LOCK_DIR = Path("/tmp/cronwatch/locks")


@dataclass
class LockOptions:
    enabled: bool = True
    lock_dir: Path = _LOCK_DIR
    stale_after: int = 3600  # seconds before a lock is considered stale


@dataclass
class LockResult:
    acquired: bool
    lock_path: Path
    existing_pid: int | None = None


def _lock_path(job_name: str, lock_dir: Path) -> Path:
    safe = job_name.replace("/", "_").replace(" ", "_")
    return lock_dir / f"{safe}.lock"


def acquire_lock(job_name: str, opts: LockOptions) -> LockResult:
    """Attempt to acquire a lock for *job_name*. Returns a LockResult."""
    path = _lock_path(job_name, opts.lock_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        try:
            age = time.time() - path.stat().st_mtime
            pid = int(path.read_text().strip())
        except (ValueError, OSError):
            pid = None
            age = opts.stale_after + 1  # treat unreadable lock as stale

        if age < opts.stale_after:
            return LockResult(acquired=False, lock_path=path, existing_pid=pid)

        # stale lock — remove and proceed
        path.unlink(missing_ok=True)

    path.write_text(str(os.getpid()))
    return LockResult(acquired=True, lock_path=path)


def release_lock(lock_path: Path) -> None:
    """Remove the lock file if it still belongs to the current process."""
    if not lock_path.exists():
        return
    try:
        pid = int(lock_path.read_text().strip())
        if pid == os.getpid():
            lock_path.unlink(missing_ok=True)
    except (ValueError, OSError):
        pass
