"""cronwatch/routing.py

Notification routing: direct job results to specific notification channels
based on configurable rules (e.g., route by tag, exit code, or job name).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from cronwatch.runner import JobResult


@dataclass
class RouteRule:
    """A single routing rule mapping a condition to a set of channels."""

    # Channels to route to when this rule matches (e.g. ["slack", "email"])
    channels: List[str] = field(default_factory=list)

    # Optional: only match jobs whose name contains this substring
    job_name_contains: Optional[str] = None

    # Optional: only match if exit code is in this list
    exit_codes: Optional[List[int]] = None

    # Optional: only match if any of these tags are present on the result
    tags: Optional[List[str]] = None

    # Only fire on failure (exit_code != 0)
    on_failure_only: bool = False

    # Only fire on success (exit_code == 0)
    on_success_only: bool = False


@dataclass
class RoutingOptions:
    """Top-level routing configuration."""

    enabled: bool = False
    rules: List[RouteRule] = field(default_factory=list)
    # Channels used when no rule matches
    default_channels: List[str] = field(default_factory=lambda: ["slack", "email"])

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoutingOptions":
        raw = data.get("routing", {})
        rules = [
            RouteRule(
                channels=r.get("channels", []),
                job_name_contains=r.get("job_name_contains"),
                exit_codes=r.get("exit_codes"),
                tags=r.get("tags"),
                on_failure_only=bool(r.get("on_failure_only", False)),
                on_success_only=bool(r.get("on_success_only", False)),
            )
            for r in raw.get("rules", [])
        ]
        return cls(
            enabled=bool(raw.get("enabled", False)),
            rules=rules,
            default_channels=raw.get("default_channels", ["slack", "email"]),
        )


@dataclass
class RoutingResult:
    """Result of evaluating routing rules against a job result."""

    channels: List[str]
    matched_rule: Optional[RouteRule]

    def ok(self) -> bool:
        return bool(self.channels)

    def summary(self) -> str:
        if self.matched_rule:
            return f"Routed to {self.channels} via matched rule"
        return f"Routed to {self.channels} via default channels"


def _rule_matches(rule: RouteRule, result: JobResult) -> bool:
    """Return True if the rule conditions are satisfied by the job result."""
    if rule.on_failure_only and result.exit_code == 0:
        return False
    if rule.on_success_only and result.exit_code != 0:
        return False
    if rule.job_name_contains and rule.job_name_contains not in result.command:
        return False
    if rule.exit_codes is not None and result.exit_code not in rule.exit_codes:
        return False
    if rule.tags is not None:
        result_tags: List[str] = getattr(result, "tags", []) or []
        if not any(t in result_tags for t in rule.tags):
            return False
    return True


def resolve_channels(options: RoutingOptions, result: JobResult) -> RoutingResult:
    """Evaluate routing rules in order and return the first match.

    Falls back to ``default_channels`` when no rule matches or routing is
    disabled.
    """
    if not options.enabled:
        return RoutingResult(channels=options.default_channels, matched_rule=None)

    for rule in options.rules:
        if _rule_matches(rule, result):
            return RoutingResult(channels=rule.channels, matched_rule=rule)

    return RoutingResult(channels=options.default_channels, matched_rule=None)
