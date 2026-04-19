"""Output line prefixing for cron job logs."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PrefixOptions:
    enabled: bool = False
    template: str = "[{job}]"
    include_timestamp: bool = False
    timestamp_format: str = "%Y-%m-%dT%H:%M:%S"

    @classmethod
    def from_dict(cls, data: dict) -> "PrefixOptions":
        return cls(
            enabled=bool(data.get("enabled", False)),
            template=str(data.get("template", "[{job}]")),
            include_timestamp=bool(data.get("include_timestamp", False)),
            timestamp_format=str(data.get("timestamp_format", "%Y-%m-%dT%H:%M:%S")),
        )


@dataclass
class PrefixResult:
    original: str
    prefixed: str
    job: str
    lines_processed: int

    @property
    def ok(self) -> bool:
        return True

    def summary(self) -> str:
        return f"Prefixed {self.lines_processed} line(s) for job '{self.job}'"


def _build_prefix(opts: PrefixOptions, job: str, ts: Optional[str] = None) -> str:
    prefix = opts.template.format(job=job)
    if opts.include_timestamp and ts:
        prefix = f"{ts} {prefix}"
    return prefix


def apply_prefix(output: str, job: str, opts: PrefixOptions) -> PrefixResult:
    """Prefix each non-empty line of output with a job-aware prefix."""
    if not opts.enabled or not output:
        return PrefixResult(
            original=output,
            prefixed=output,
            job=job,
            lines_processed=0,
        )

    import datetime

    ts: Optional[str] = None
    if opts.include_timestamp:
        ts = datetime.datetime.now().strftime(opts.timestamp_format)

    prefix = _build_prefix(opts, job, ts)
    lines = output.splitlines()
    prefixed_lines = [f"{prefix} {line}" if line.strip() else line for line in lines]
    prefixed = "\n".join(prefixed_lines)

    return PrefixResult(
        original=output,
        prefixed=prefixed,
        job=job,
        lines_processed=len([l for l in lines if l.strip()]),
    )
