"""Environment variable validation for cron job execution context."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EnvCheckOptions:
    """Options controlling environment variable validation."""

    required: List[str] = field(default_factory=list)
    expected: Dict[str, str] = field(default_factory=dict)
    warn_only: bool = False


@dataclass
class EnvCheckResult:
    """Result of an environment validation pass."""

    missing: List[str] = field(default_factory=list)
    mismatched: Dict[str, tuple] = field(default_factory=dict)  # name -> (expected, actual)
    passed: bool = True

    @property
    def ok(self) -> bool:
        return self.passed and not self.missing and not self.mismatched

    def summary(self) -> str:
        parts: List[str] = []
        if self.missing:
            parts.append("Missing vars: " + ", ".join(self.missing))
        if self.mismatched:
            details = "; ".join(
                f"{k}='{actual}' (expected '{exp}')"
                for k, (exp, actual) in self.mismatched.items()
            )
            parts.append("Mismatched vars: " + details)
        if not parts:
            return "All environment checks passed."
        return " | ".join(parts)


def check_env(options: EnvCheckOptions) -> EnvCheckResult:
    """Validate the current environment against the given options.

    Args:
        options: Describes which variables are required or must match a value.

    Returns:
        An EnvCheckResult describing any problems found.
    """
    result = EnvCheckResult()

    for var in options.required:
        if var not in os.environ:
            result.missing.append(var)

    for var, expected_val in options.expected.items():
        actual: Optional[str] = os.environ.get(var)
        if actual is None:
            if var not in result.missing:
                result.missing.append(var)
        elif actual != expected_val:
            result.mismatched[var] = (expected_val, actual)

    if result.missing or result.mismatched:
        result.passed = options.warn_only

    return result


def env_check_from_config(raw: dict) -> EnvCheckOptions:
    """Build EnvCheckOptions from a raw config dict (e.g. loaded from YAML)."""
    return EnvCheckOptions(
        required=raw.get("required", []),
        expected=raw.get("expected", {}),
        warn_only=bool(raw.get("warn_only", False)),
    )
