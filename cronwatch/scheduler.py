"""Cron schedule parsing and next-run calculation utilities."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional

# Supported named schedules
_NAMED_SCHEDULES: dict[str, str] = {
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
    "@monthly": "0 0 1 * *",
    "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *",
}

_CRON_PATTERN = re.compile(
    r"^(\*|\d+)\s+(\*|\d+)\s+(\*|\d+)\s+(\*|\d+)\s+(\*|\d+)$"
)


def _resolve_expression(expression: str) -> str:
    """Expand named shortcuts into standard 5-field cron expressions."""
    return _NAMED_SCHEDULES.get(expression.strip(), expression.strip())


def is_valid_cron(expression: str) -> bool:
    """Return True if *expression* is a valid 5-field cron string or named shortcut."""
    resolved = _resolve_expression(expression)
    return bool(_CRON_PATTERN.match(resolved))


def _field_matches(field: str, value: int) -> bool:
    """Check whether a single cron field matches *value*."""
    if field == "*":
        return True
    return int(field) == value


def next_run(expression: str, after: Optional[datetime] = None) -> datetime:
    """Return the next datetime when *expression* would fire.

    Supports only simple ``*`` or exact-value fields (no ranges/steps).
    Raises ``ValueError`` for invalid expressions.
    """
    resolved = _resolve_expression(expression)
    if not is_valid_cron(expression):
        raise ValueError(f"Invalid cron expression: {expression!r}")

    parts = resolved.split()
    minute, hour, dom, month, dow = parts

    base = (after or datetime.now()).replace(second=0, microsecond=0)
    candidate = base + timedelta(minutes=1)

    # Brute-force search up to 1 year ahead
    for _ in range(525_600):  # minutes in a year
        if (
            _field_matches(month, candidate.month)
            and _field_matches(dom, candidate.day)
            and _field_matches(dow, candidate.weekday())
            and _field_matches(hour, candidate.hour)
            and _field_matches(minute, candidate.minute)
        ):
            return candidate
        candidate += timedelta(minutes=1)

    raise RuntimeError("Could not determine next run within one year.")  # pragma: no cover
