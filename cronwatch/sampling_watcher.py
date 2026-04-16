"""Sampling watcher: gate downstream actions based on sampling decision."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from cronwatch.runner import JobResult
from cronwatch.sampling import SamplingOptions, SamplingResult, should_sample


@dataclass
class SamplingWatchOptions:
    sampling: SamplingOptions
    only_on_failure: bool = False  # when True, sampling only applies to failures

    @classmethod
    def from_dict(cls, d: dict) -> "SamplingWatchOptions":
        return cls(
            sampling=SamplingOptions.from_dict(d.get("sampling", {})),
            only_on_failure=bool(d.get("only_on_failure", False)),
        )


def check_sampling(opts: SamplingWatchOptions, result: JobResult) -> Optional[SamplingResult]:
    """Return a SamplingResult if sampling applies, else None (meaning: proceed).

    Returns None when sampling is disabled or when only_on_failure=True and job succeeded.
    Returns a SamplingResult (which may say sampled=False → skip) otherwise.
    """
    if not opts.sampling.enabled:
        return None
    if opts.only_on_failure and result.success:
        return None
    return should_sample(opts.sampling)


def format_skip_notice(result: SamplingResult) -> str:
    return (
        f"[cronwatch/sampling] action skipped "
        f"(rate={result.rate:.2f}, sampled={result.sampled})"
    )
