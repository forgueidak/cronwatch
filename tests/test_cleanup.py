"""Tests for cronwatch.cleanup."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from cronwatch.cleanup import find_old_files, purge_old_files


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _touch(path: Path, age_days: float) -> None:
    """Create *path* and back-date its mtime by *age_days* days."""
    path.write_text("data")
    old_time = time.time() - age_days * 86400
    import os
    os.utime(path, (old_time, old_time))


# ---------------------------------------------------------------------------
# find_old_files
# ---------------------------------------------------------------------------

def test_find_old_files_missing_directory(tmp_path: Path) -> None:
    result = find_old_files(tmp_path / "nonexistent", max_age_days=7)
    assert result == []


def test_find_old_files_empty_directory(tmp_path: Path) -> None:
    assert find_old_files(tmp_path, max_age_days=7) == []


def test_find_old_files_returns_only_old(tmp_path: Path) -> None:
    _touch(tmp_path / "old.log", age_days=10)
    _touch(tmp_path / "new.log", age_days=1)

    result = find_old_files(tmp_path, max_age_days=7)

    assert len(result) == 1
    assert result[0].name == "old.log"


def test_find_old_files_ignores_subdirs(tmp_path: Path) -> None:
    sub = tmp_path / "subdir"
    sub.mkdir()
    _touch(tmp_path / "old.log", age_days=30)

    result = find_old_files(tmp_path, max_age_days=7)

    names = [p.name for p in result]
    assert "subdir" not in names
    assert "old.log" in names


# ---------------------------------------------------------------------------
# purge_old_files
# ---------------------------------------------------------------------------

def test_purge_deletes_old_files(tmp_path: Path) -> None:
    _touch(tmp_path / "old.log", age_days=15)
    _touch(tmp_path / "recent.log", age_days=2)

    deleted, skipped = purge_old_files(tmp_path, max_age_days=7)

    assert deleted == 1
    assert skipped == 0
    assert not (tmp_path / "old.log").exists()
    assert (tmp_path / "recent.log").exists()


def test_purge_dry_run_does_not_delete(tmp_path: Path) -> None:
    _touch(tmp_path / "old.log", age_days=20)

    deleted, skipped = purge_old_files(tmp_path, max_age_days=7, dry_run=True)

    assert deleted == 0
    assert skipped == 1
    assert (tmp_path / "old.log").exists()


def test_purge_missing_directory_returns_zeros(tmp_path: Path) -> None:
    deleted, skipped = purge_old_files(tmp_path / "ghost", max_age_days=7)
    assert (deleted, skipped) == (0, 0)


def test_purge_nothing_to_delete(tmp_path: Path) -> None:
    _touch(tmp_path / "new.log", age_days=1)

    deleted, skipped = purge_old_files(tmp_path, max_age_days=7)

    assert (deleted, skipped) == (0, 0)
