"""Output redaction: scrub sensitive patterns from job stdout/stderr."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


_PLACEHOLDER = "[REDACTED]"


@dataclass
class RedactOptions:
    enabled: bool = False
    patterns: List[str] = field(default_factory=list)
    placeholder: str = _PLACEHOLDER

    @classmethod
    def from_dict(cls, data: dict) -> "RedactOptions":
        raw = data.get("redact", {})
        return cls(
            enabled=bool(raw.get("enabled", False)),
            patterns=list(raw.get("patterns", [])),
            placeholder=str(raw.get("placeholder", _PLACEHOLDER)),
        )


@dataclass
class RedactResult:
    original: str
    redacted: str
    redaction_count: int

    @property
    def ok(self) -> bool:
        """True when no redactions were needed (nothing sensitive found)."""
        return self.redaction_count == 0

    def summary(self) -> str:
        if self.ok:
            return "no sensitive patterns detected"
        return f"{self.redaction_count} sensitive pattern(s) redacted"


def _compile_patterns(patterns: List[str]) -> List[re.Pattern]:
    compiled = []
    for p in patterns:
        try:
            compiled.append(re.compile(p))
        except re.error:
            pass  # skip invalid patterns silently
    return compiled


def redact_text(
    text: str,
    opts: RedactOptions,
    _compiled: Optional[List[re.Pattern]] = None,
) -> RedactResult:
    """Apply all redaction patterns to *text* and return a RedactResult."""
    if not opts.enabled or not opts.patterns:
        return RedactResult(original=text, redacted=text, redaction_count=0)

    patterns = _compiled if _compiled is not None else _compile_patterns(opts.patterns)
    result = text
    count = 0
    for pat in patterns:
        new, n = pat.subn(opts.placeholder, result)
        result = new
        count += n
    return RedactResult(original=text, redacted=result, redaction_count=count)


def apply_redaction(stdout: str, stderr: str, opts: RedactOptions) -> tuple[str, str]:
    """Convenience wrapper: redact both stdout and stderr, return cleaned pair."""
    compiled = _compile_patterns(opts.patterns)
    r_out = redact_text(stdout, opts, compiled)
    r_err = redact_text(stderr, opts, compiled)
    return r_out.redacted, r_err.redacted
