"""Integrate metrics recording into the cronwatch watch pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwatch.metrics import MetricPoint, record_metric, summarize_metrics, MetricsSummary
from cronwatch.runner import JobResult


@dataclass
class MetricsOptions:
    enabled: bool = False
    metrics_dir: str = "~/.cronwatch/metrics"
    retain_limit: Optional[int] = None
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "MetricsOptions":
        return cls(
            enabled=data.get("enabled", False),
            metrics_dir=data.get("metrics_dir", "~/.cronwatch/metrics"),
            retain_limit=data.get("retain_limit"),
            tags=data.get("tags", []),
        )


def record_job_metric(result: JobResult, opts: MetricsOptions) -> Optional[MetricPoint]:
    """Record a MetricPoint for the given JobResult if metrics are enabled."""
    if not opts.enabled:
        return None

    metrics_dir = Path(opts.metrics_dir).expanduser()
    point = MetricPoint(
        command=result.command,
        success=result.success,
        duration=result.duration,
        exit_code=result.exit_code,
        tags=list(opts.tags),
    )
    record_metric(point, metrics_dir)
    return point


def get_job_summary(command: str, opts: MetricsOptions) -> Optional[MetricsSummary]:
    """Return a MetricsSummary for *command* using the configured metrics directory."""
    if not opts.enabled:
        return None
    metrics_dir = Path(opts.metrics_dir).expanduser()
    return summarize_metrics(command, metrics_dir, limit=opts.retain_limit)


def format_metrics_text(summary: MetricsSummary) -> str:
    """Return a human-readable string for a MetricsSummary."""
    lines = [
        f"Metrics for: {summary.command}",
        f"  Total runs : {summary.total}",
        f"  Successes  : {summary.successes}",
        f"  Failures   : {summary.failures}",
        f"  Success %%  : {summary.success_rate:.1f}%%",
        f"  Avg dur    : {summary.avg_duration:.2f}s",
        f"  Min dur    : {summary.min_duration:.2f}s",
        f"  Max dur    : {summary.max_duration:.2f}s",
    ]
    return "\n".join(lines)
