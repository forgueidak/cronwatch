"""pipeline.py — Ordered execution pipeline for pre/post job hooks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from cronwatch.runner import JobResult


@dataclass
class PipelineStep:
    name: str
    fn: Callable[[JobResult], Optional[str]]
    on_failure_only: bool = False
    on_success_only: bool = False


@dataclass
class PipelineResult:
    steps_run: List[str] = field(default_factory=list)
    steps_skipped: List[str] = field(default_factory=list)
    errors: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> str:
        parts = [f"ran={len(self.steps_run)}", f"skipped={len(self.steps_skipped)}"]
        if self.errors:
            parts.append(f"errors={list(self.errors.keys())}")
        return " ".join(parts)


@dataclass
class PipelineOptions:
    steps: List[PipelineStep] = field(default_factory=list)
    stop_on_error: bool = False

    @staticmethod
    def from_dict(d: dict) -> "PipelineOptions":
        return PipelineOptions(
            stop_on_error=bool(d.get("stop_on_error", False)),
        )


def run_pipeline(result: JobResult, opts: PipelineOptions) -> PipelineResult:
    """Run all registered pipeline steps against a JobResult."""
    pr = PipelineResult()
    for step in opts.steps:
        if step.on_failure_only and result.success:
            pr.steps_skipped.append(step.name)
            continue
        if step.on_success_only and not result.success:
            pr.steps_skipped.append(step.name)
            continue
        try:
            step.fn(result)
            pr.steps_run.append(step.name)
        except Exception as exc:  # noqa: BLE001
            pr.errors[step.name] = str(exc)
            pr.steps_run.append(step.name)
            if opts.stop_on_error:
                break
    return pr
