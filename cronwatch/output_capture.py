"""Output capture options and truncation utilities for cron job results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


_DEFAULT_MAX_BYTES = 64 * 1024  # 64 KB
_DEFAULT_MAX_LINES = 500


@dataclass
class OutputCaptureOptions:
    """Controls how stdout/stderr are captured and stored."""
    enabled: bool = True
    max_bytes: int = _DEFAULT_MAX_BYTES
    max_lines: int = _DEFAULT_MAX_LINES
    truncation_marker: str = "... [truncated]"
    capture_stdout: bool = True
    capture_stderr: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "OutputCaptureOptions":
        return cls(
            enabled=data.get("enabled", True),
            max_bytes=data.get("max_bytes", _DEFAULT_MAX_BYTES),
            max_lines=data.get("max_lines", _DEFAULT_MAX_LINES),
            truncation_marker=data.get("truncation_marker", "... [truncated]"),
            capture_stdout=data.get("capture_stdout", True),
            capture_stderr=data.get("capture_stderr", True),
        )


@dataclass
class CaptureResult:
    """Holds the (possibly truncated) output from a job run."""
    stdout: str = ""
    stderr: str = ""
    stdout_truncated: bool = False
    stderr_truncated: bool = False

    @property
    def ok(self) -> bool:
        return not (self.stdout_truncated or self.stderr_truncated)

    def summary(self) -> str:
        parts = []
        if self.stdout_truncated:
            parts.append("stdout truncated")
        if self.stderr_truncated:
            parts.append("stderr truncated")
        return ", ".join(parts) if parts else "output within limits"


def _truncate(text: str, max_bytes: int, max_lines: int, marker: str) -> tuple[str, bool]:
    """Truncate *text* by byte length and line count; return (result, was_truncated)."""
    if not text:
        return text, False

    lines = text.splitlines(keepends=True)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        text = "".join(lines) + marker + "\n"
        return text, True

    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) > max_bytes:
        truncated = encoded[:max_bytes].decode("utf-8", errors="replace")
        return truncated + marker, True

    return text, False


def apply_capture_options(
    stdout: str,
    stderr: str,
    opts: Optional[OutputCaptureOptions] = None,
) -> CaptureResult:
    """Apply capture limits to raw stdout/stderr strings."""
    if opts is None:
        opts = OutputCaptureOptions()

    if not opts.enabled:
        return CaptureResult(stdout=stdout, stderr=stderr)

    out, out_trunc = _truncate(stdout if opts.capture_stdout else "",
                                opts.max_bytes, opts.max_lines, opts.truncation_marker)
    err, err_trunc = _truncate(stderr if opts.capture_stderr else "",
                                opts.max_bytes, opts.max_lines, opts.truncation_marker)

    return CaptureResult(
        stdout=out,
        stderr=err,
        stdout_truncated=out_trunc,
        stderr_truncated=err_trunc,
    )
