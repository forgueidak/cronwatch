"""Tests for cronwatch.metrics."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwatch.metrics import (
    MetricPoint,
    load_metrics,
    record_metric,
    summarize_metrics,
)


@pytest.fixture()
def metrics_dir(tmp_path: Path) -> Path:
    return tmp_path / "metrics"


def _point(command: str = "echo hi", success: bool = True, duration: float = 1.0, ts: float = 0.0) -> MetricPoint:
    return MetricPoint(command=command, success=success, duration=duration, timestamp=ts or time.time())


class TestMetricPoint:
    def test_to_dict_round_trip(self):
        p = _point()
        d = p.to_dict()
        p2 = MetricPoint.from_dict(d)
        assert p2.command == p.command
        assert p2.success == p.success
        assert p2.duration == p.duration

    def test_from_dict_defaults(self):
        p = MetricPoint.from_dict({"command": "x", "success": True, "duration": 2.5})
        assert p.exit_code == 0
        assert p.tags == []


def test_record_metric_creates_file(metrics_dir: Path):
    p = _point()
    record_metric(p, metrics_dir)
    files = list(metrics_dir.iterdir())
    assert len(files) == 1


def test_record_metric_appends(metrics_dir: Path):
    p = _point()
    record_metric(p, metrics_dir)
    record_metric(p, metrics_dir)
    path = next(metrics_dir.iterdir())
    lines = [l for l in path.read_text().splitlines() if l.strip()]
    assert len(lines) == 2


def test_record_metric_valid_json(metrics_dir: Path):
    p = _point(command="backup.sh")
    record_metric(p, metrics_dir)
    path = next(metrics_dir.iterdir())
    data = json.loads(path.read_text().strip())
    assert data["command"] == "backup.sh"


def test_load_metrics_missing_dir(metrics_dir: Path):
    result = load_metrics("no-command", metrics_dir)
    assert result == []


def test_load_metrics_returns_newest_first(metrics_dir: Path):
    for i in range(3):
        record_metric(_point(ts=float(i)), metrics_dir)
    points = load_metrics("echo hi", metrics_dir)
    assert points[0].timestamp >= points[-1].timestamp


def test_load_metrics_respects_limit(metrics_dir: Path):
    for i in range(5):
        record_metric(_point(ts=float(i)), metrics_dir)
    points = load_metrics("echo hi", metrics_dir, limit=3)
    assert len(points) == 3


def test_summarize_metrics_none_when_empty(metrics_dir: Path):
    assert summarize_metrics("missing", metrics_dir) is None


def test_summarize_metrics_counts(metrics_dir: Path):
    record_metric(_point(success=True, duration=2.0), metrics_dir)
    record_metric(_point(success=False, duration=4.0), metrics_dir)
    s = summarize_metrics("echo hi", metrics_dir)
    assert s is not None
    assert s.total == 2
    assert s.successes == 1
    assert s.failures == 1


def test_summarize_metrics_avg_duration(metrics_dir: Path):
    record_metric(_point(duration=2.0), metrics_dir)
    record_metric(_point(duration=4.0), metrics_dir)
    s = summarize_metrics("echo hi", metrics_dir)
    assert s.avg_duration == pytest.approx(3.0)
    assert s.min_duration == pytest.approx(2.0)
    assert s.max_duration == pytest.approx(4.0)


def test_summarize_success_rate_all_pass(metrics_dir: Path):
    for _ in range(4):
        record_metric(_point(success=True), metrics_dir)
    s = summarize_metrics("echo hi", metrics_dir)
    assert s.success_rate == pytest.approx(100.0)
