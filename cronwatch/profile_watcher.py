"""Integrate profile checking into the watch pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cronwatch.profile import ProfileOptions, ProfileResult, check_profile
from cronwatch.runner import JobResult


@dataclass
class ProfileWatchOptions:
    profile: ProfileOptions = field(default_factory=ProfileOptions)
    notify_on_slow: bool = True

    @classmethod
    def from_dict(cls, d: dict) -> "ProfileWatchOptions":
        return cls(
            profile=ProfileOptions.from_dict(d.get("profile", {})),
            notify_on_slow=bool(d.get("notify_on_slow", True)),
        )


def watch_profile(result: JobResult, opts: ProfileWatchOptions) -> Optional[ProfileResult]:
    """Run profile check and return result if slow (and notify enabled)."""
    pr = check_profile(result, opts.profile)
    if pr is None:
        return None
    if pr.slow and opts.notify_on_slow:
        return pr
    if not pr.slow:
        return pr
    return pr


def format_slow_notice(result: JobResult, pr: ProfileResult) -> str:
    lines = [
        f"[cronwatch] Slow job detected: {result.command}",
        pr.message,
    ]
    if pr.mean is not None:
        lines.append(f"  Mean: {pr.mean:.2f}s  Threshold: {pr.threshold:.2f}s  Actual: {pr.duration:.2f}s")
    return "\n".join(lines)
