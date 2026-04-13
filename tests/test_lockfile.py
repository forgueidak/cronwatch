"""Tests for cronwatch.lockfile."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from cronwatch.lockfile import (
    LockOptions,
    acquire_lock,
    release_lock,
    _lock_path,
)


@pytest.fixture()
def lock_dir(tmp_path: Path) -> Path:
    d = tmp_path / "locks"
    d.mkdir()
    return d


def _opts(lock_dir: Path, stale_after: int = 3600) -> LockOptions:
    return LockOptions(enabled=True, lock_dir=lock_dir, stale_after=stale_after)


# ---------------------------------------------------------------------------
# _lock_path
# ---------------------------------------------------------------------------

def test_lock_path_sanitizes_slashes(lock_dir: Path) -> None:
    p = _lock_path("my/job name", lock_dir)
    assert "/" not in p.name
    assert " " not in p.name


# ---------------------------------------------------------------------------
# acquire_lock
# ---------------------------------------------------------------------------

def test_acquire_lock_creates_file(lock_dir: Path) -> None:
    result = acquire_lock("backup", _opts(lock_dir))
    assert result.acquired is True
    assert result.lock_path.exists()


def test_acquire_lock_writes_pid(lock_dir: Path) -> None:
    result = acquire_lock("backup", _opts(lock_dir))
    pid = int(result.lock_path.read_text().strip())
    assert pid == os.getpid()


def test_acquire_lock_fails_when_active_lock_exists(lock_dir: Path) -> None:
    opts = _opts(lock_dir)
    first = acquire_lock("myjob", opts)
    assert first.acquired is True

    second = acquire_lock("myjob", opts)
    assert second.acquired is False
    assert second.existing_pid == os.getpid()


def test_acquire_lock_succeeds_after_stale_lock(lock_dir: Path) -> None:
    opts = _opts(lock_dir, stale_after=1)
    first = acquire_lock("stale_job", opts)
    assert first.acquired is True

    # backdate the mtime so the lock appears stale
    os.utime(first.lock_path, (time.time() - 10, time.time() - 10))

    second = acquire_lock("stale_job", opts)
    assert second.acquired is True


def test_acquire_lock_handles_unreadable_lock(lock_dir: Path) -> None:
    opts = _opts(lock_dir, stale_after=1)
    path = lock_dir / "bad_job.lock"
    path.write_text("not-a-pid")
    os.utime(path, (time.time() - 10, time.time() - 10))

    result = acquire_lock("bad_job", opts)
    assert result.acquired is True


# ---------------------------------------------------------------------------
# release_lock
# ---------------------------------------------------------------------------

def test_release_lock_removes_file(lock_dir: Path) -> None:
    result = acquire_lock("rel_job", _opts(lock_dir))
    assert result.lock_path.exists()
    release_lock(result.lock_path)
    assert not result.lock_path.exists()


def test_release_lock_ignores_missing_file(lock_dir: Path) -> None:
    p = lock_dir / "ghost.lock"
    release_lock(p)  # should not raise


def test_release_lock_does_not_remove_foreign_pid(lock_dir: Path, tmp_path: Path) -> None:
    p = lock_dir / "foreign.lock"
    p.write_text("99999")  # some other PID
    release_lock(p)
    assert p.exists()  # should NOT be removed
