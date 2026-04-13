"""Output filtering: truncate, redact, or pattern-match job stdout/stderr."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class OutputFilterOptions:
    max_lines: int = 100
    max_bytes: int = 8192
    redact_patterns: List[str] = field(default_factory=list)
    include_pattern: Optional[str] = None
    exclude_pattern: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "OutputFilterOptions":
        return cls(
            max_lines=int(data.get("max_lines", 100)),
            max_bytes=int(data.get("max_bytes", 8192)),
            redact_patterns=list(data.get("redact_patterns", [])),
            include_pattern=data.get("include_pattern"),
            exclude_pattern=data.get("exclude_pattern"),
        )


@dataclass
class FilterResult:
    text: str
    truncated: bool
    redacted_count: int
    lines_removed: int

    @property
    def ok(self) -> bool:
        return not self.truncated and self.redacted_count == 0


def _redact(text: str, patterns: List[str]) -> tuple[str, int]:
    count = 0
    for pat in patterns:
        new_text, n = re.subn(pat, "[REDACTED]", text)
        text = new_text
        count += n
    return text, count


def _filter_lines(
    text: str,
    include_pattern: Optional[str],
    exclude_pattern: Optional[str],
) -> tuple[str, int]:
    lines = text.splitlines(keepends=True)
    original = len(lines)
    if include_pattern:
        lines = [l for l in lines if re.search(include_pattern, l)]
    if exclude_pattern:
        lines = [l for l in lines if not re.search(exclude_pattern, l)]
    removed = original - len(lines)
    return "".join(lines), removed


def apply_output_filter(text: str, opts: OutputFilterOptions) -> FilterResult:
    """Apply all configured filters to output text."""
    filtered, lines_removed = _filter_lines(
        text, opts.include_pattern, opts.exclude_pattern
    )
    redacted, redacted_count = _redact(filtered, opts.redact_patterns)

    lines = redacted.splitlines(keepends=True)
    truncated = False

    if len(lines) > opts.max_lines:
        lines = lines[: opts.max_lines]
        truncated = True

    result = "".join(lines)
    if len(result.encode()) > opts.max_bytes:
        result = result.encode()[: opts.max_bytes].decode(errors="ignore")
        truncated = True

    return FilterResult(
        text=result,
        truncated=truncated,
        redacted_count=redacted_count,
        lines_removed=lines_removed,
    )
