"""Tests for cronwatch.metrics_watcher."""

from __future__ import annotations

from pathlib import Path

import pytest

from cronwatch.metrics_watcher import (
    MetricsOptions,
    format_metrics_text,
    get_job_summary,
    record_job_metric,
)
from cronwatch.runner import JobResult


def _make_result(
    command: str = "echo hi",
    success: bool = True,
    exit_code: int = 0,
    duration: float = 1.5,
) -> JobResult:
    return JobResult(
        command=command,
        success=success,
        exit_code=exit_code,
        stdout="ok",
        stderr="",
        duration=duration,
    )


def _opts(tmp_path: Path, enabled: bool = True, tags=None) -> MetricsOptions:
    return MetricsOptions(
        enabled=enabled,
        metrics_dir=str(tmp_path / "metrics"),
        tags=tags or [],
    )


class TestMetricsOptions:
    def test_defaults(self):
        o = MetricsOptions()
        assert o.enabled is False
        assert "metrics" in o.metrics_dir

    def test_from_dict(self):
        o = MetricsOptions.from_dict({"enabled": True, "tags": ["prod"]})
        assert o.enabled is True
        assert o.tags == ["prod"]

    def test_from_dict_defaults(self):
        o = MetricsOptions.from_dict({})
        assert o.enabled is False
        assert o.retain_limit is None


def test_record_job_metric_disabled_returns_none(tmp_path):
    result = _make_result()
    opts = _opts(tmp_path, enabled=False)
    assert record_job_metric(result, opts) is None


def test_record_job_metric_creates_point(tmp_path):
    result = _make_result()
    opts = _opts(tmp_path)
    point = record_job_metric(result, opts)
    assert point is not None
    assert point.command == result.command
    assert point.success == result.success


def test_record_job_metric_stores_tags(tmp_path):
    result = _make_result()
    opts = _opts(tmp_path, tags=["nightly", "prod"])
    point = record_job_metric(result, opts)
    assert point.tags == ["nightly", "prod"]


def test_record_job_metric_creates_file(tmp_path):
    result = _make_result()
    opts = _opts(tmp_path)
    record_job_metric(result, opts)
    metrics_dir = Path(opts.metrics_dir)
    assert any(metrics_dir.iterdir())


def test_get_job_summary_disabled_returns_none(tmp_path):
    opts = _opts(tmp_path, enabled=False)
    assert get_job_summary("echo hi", opts) is None


def test_get_job_summary_no_data_returns_none(tmp_path):
    opts = _opts(tmp_path)
    assert get_job_summary("echo hi", opts) is None


def test_get_job_summary_returns_summary(tmp_path):
    opts = _opts(tmp_path)
    for _ in range(3):
        record_job_metric(_make_result(), opts)
    s = get_job_summary("echo hi", opts)
    assert s is not None
    assert s.total == 3


def test_format_metrics_text_contains_command(tmp_path):
    opts = _opts(tmp_path)
    record_job_metric(_make_result(), opts)
    s = get_job_summary("echo hi", opts)
    text = format_metrics_text(s)
    assert "echo hi" in text
    assert "Total" in text
    assert "Success" in text
