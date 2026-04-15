"""Cleanup utilities for pruning old cronwatch log and history files."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import List, Tuple


def _age_days(path: Path) -> float:
    """Return the age of a file in days."""
    mtime = path.stat().st_mtime
    return (time.time() - mtime) / 86400


def find_old_files(directory: str | Path, max_age_days: int) -> List[Path]:
    """Return a list of files in *directory* older than *max_age_days*.

    Only regular files are considered; sub-directories are ignored.
    """
    root = Path(directory)
    if not root.is_dir():
        return []

    old: List[Path] = []
    for entry in root.iterdir():
        if entry.is_file() and _age_days(entry) > max_age_days:
            old.append(entry)
    return sorted(old)


def purge_old_files(
    directory: str | Path,
    max_age_days: int,
    dry_run: bool = False,
) -> Tuple[int, int]:
    """Delete files in *directory* that are older than *max_age_days*.

    Args:
        directory: Directory to scan.
        max_age_days: Files older than this many days are deleted.
        dry_run: When *True*, files are identified but not removed.

    Returns:
        A ``(deleted, skipped)`` tuple where *deleted* is the number of
        files removed and *skipped* is the number that would have been
        removed in a non-dry run.
    """
    targets = find_old_files(directory, max_age_days)
    deleted = 0
    skipped = 0

    for path in targets:
        if dry_run:
            skipped += 1
        else:
            try:
                os.remove(path)
                deleted += 1
            except OSError:
                pass  # best-effort; skip files we cannot remove

    return deleted, skipped


def find_files_by_pattern(
    directory: str | Path,
    pattern: str,
    max_age_days: int | None = None,
) -> List[Path]:
    """Return files in *directory* matching a glob *pattern*.

    Args:
        directory: Directory to scan.
        pattern: Glob pattern to match filenames against (e.g. ``"*.log"``).
        max_age_days: When provided, only files older than this many days
            are included.  When *None*, all matching files are returned.

    Returns:
        A sorted list of :class:`~pathlib.Path` objects for matching files.
    """
    root = Path(directory)
    if not root.is_dir():
        return []

    matches = [
        entry
        for entry in root.glob(pattern)
        if entry.is_file()
        and (max_age_days is None or _age_days(entry) > max_age_days)
    ]
    return sorted(matches)
