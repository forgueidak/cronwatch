"""Snapshot-aware watcher: extend the base watcher to detect output changes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cronwatch.runner import JobResult
from cronwatch.snapshot import DEFAULT_SNAPSHOT_DIR, output_changed, save_snapshot


@dataclass
class SnapshotOptions:
    enabled: bool = False
    notify_on_change: bool = True
    dir: Path = field(default_factory=lambda: DEFAULT_SNAPSHOT_DIR)


@dataclass
class SnapshotCheckResult:
    changed: bool
    previous_exists: bool
    should_notify: bool


def check_snapshot(
    result: JobResult,
    options: SnapshotOptions,
) -> Optional[SnapshotCheckResult]:
    """Compare result stdout against the last snapshot.

    Returns None when snapshots are disabled or the job failed
    (we only snapshot successful runs).
    """
    if not options.enabled:
        return None
    if result.returncode != 0:
        return None

    snap_dir = Path(options.dir)
    stdout = result.stdout or ""

    from cronwatch.snapshot import load_snapshot  # local import to avoid cycles
    previous = load_snapshot(result.command, base_dir=snap_dir)
    changed = output_changed(result.command, stdout, base_dir=snap_dir)

    # Persist the latest output regardless of change
    save_snapshot(result.command, stdout, base_dir=snap_dir)

    return SnapshotCheckResult(
        changed=changed,
        previous_exists=previous is not None,
        should_notify=changed and options.notify_on_change,
    )


def format_change_notice(result: JobResult, snap_result: SnapshotCheckResult) -> str:
    """Return a human-readable notice about an output change."""
    if not snap_result.changed:
        return ""
    if not snap_result.previous_exists:
        return f"[snapshot] First snapshot recorded for: {result.command}"
    return (
        f"[snapshot] Output changed for: {result.command}\n"
        f"New preview: {(result.stdout or '')[:120]}"
    )
