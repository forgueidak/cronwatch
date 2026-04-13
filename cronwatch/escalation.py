"""Escalation policy: notify different channels based on consecutive failure count."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EscalationLevel:
    after_failures: int
    channels: List[str] = field(default_factory=list)
    message_prefix: str = ""

    @staticmethod
    def from_dict(d: dict) -> "EscalationLevel":
        return EscalationLevel(
            after_failures=int(d.get("after_failures", 1)),
            channels=list(d.get("channels", [])),
            message_prefix=str(d.get("message_prefix", "")),
        )


@dataclass
class EscalationOptions:
    enabled: bool = False
    levels: List[EscalationLevel] = field(default_factory=list)

    @staticmethod
    def from_dict(d: dict) -> "EscalationOptions":
        levels = [
            EscalationLevel.from_dict(lv)
            for lv in d.get("levels", [])
        ]
        levels.sort(key=lambda lv: lv.after_failures)
        return EscalationOptions(
            enabled=bool(d.get("enabled", False)),
            levels=levels,
        )


@dataclass
class EscalationResult:
    triggered: bool
    level: Optional[EscalationLevel]
    consecutive_failures: int

    @property
    def ok(self) -> bool:
        return not self.triggered

    def summary(self) -> str:
        if not self.triggered or self.level is None:
            return "No escalation triggered."
        prefix = f"{self.level.message_prefix} " if self.level.message_prefix else ""
        channels = ", ".join(self.level.channels) or "(none)"
        return (
            f"{prefix}Escalation after {self.consecutive_failures} consecutive "
            f"failure(s). Channels: {channels}"
        )


def check_escalation(
    options: EscalationOptions,
    consecutive_failures: int,
) -> EscalationResult:
    """Return the highest matching escalation level for the given failure count."""
    if not options.enabled or not options.levels:
        return EscalationResult(triggered=False, level=None,
                                consecutive_failures=consecutive_failures)

    matched: Optional[EscalationLevel] = None
    for level in options.levels:
        if consecutive_failures >= level.after_failures:
            matched = level

    if matched is None:
        return EscalationResult(triggered=False, level=None,
                                consecutive_failures=consecutive_failures)

    return EscalationResult(triggered=True, level=matched,
                            consecutive_failures=consecutive_failures)
