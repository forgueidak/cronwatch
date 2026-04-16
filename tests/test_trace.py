"""Tests for cronwatch.trace."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pytest

from cronwatch.trace import (
    TraceOptions,
    TraceSpan,
    _trace_path,
    load_traces,
    record_trace,
)


def _make_result(command="echo hi", exit_code=0):
    from cronwatch.runner import JobResult
    return JobResult(
        command=command,
        exit_code=exit_code,
        stdout="ok",
        stderr="",
        duration=1.0,
        started_at=time.time(),
        timed_out=False,
    )


def _opts(tmp_path, **kw):
    return TraceOptions(enabled=True, trace_dir=str(tmp_path), **kw)


def test_trace_span_duration_ms():
    span = TraceSpan(name="run", started_at=1000.0, ended_at=1000.5)
    assert span.duration_ms == 500.0


def test_trace_span_round_trip():
    span = TraceSpan(name="setup", started_at=1.0, ended_at=2.0)
    assert TraceSpan.from_dict(span.to_dict()).name == "setup"


def test_trace_options_defaults():
    opts = TraceOptions()
    assert opts.enabled is False
    assert opts.keep_last == 50


def test_trace_options_from_dict():
    opts = TraceOptions.from_dict({"enabled": True, "keep_last": 10, "trace_dir": "/tmp/t"})
    assert opts.enabled is True
    assert opts.keep_last == 10


def test_record_trace_disabled_returns_none(tmp_path):
    opts = TraceOptions(enabled=False, trace_dir=str(tmp_path))
    result = record_trace(_make_result(), [], opts)
    assert result is None


def test_record_trace_creates_file(tmp_path):
    opts = _opts(tmp_path)
    path = record_trace(_make_result(), [], opts)
    assert path is not None and path.exists()


def test_record_trace_valid_json(tmp_path):
    opts = _opts(tmp_path)
    spans = [TraceSpan("run", 1.0, 1.5)]
    path = record_trace(_make_result(), spans, opts)
    data = json.loads(path.read_text().splitlines()[0])
    assert data["command"] == "echo hi"
    assert len(data["spans"]) == 1
    assert data["spans"][0]["name"] == "run"


def test_load_traces_returns_newest_first(tmp_path):
    opts = _opts(tmp_path)
    for i in range(3):
        record_trace(_make_result(command=f"job_{i}"), [], opts)
    # all use same command for grouping
    opts2 = _opts(tmp_path)
    record_trace(_make_result(), [], opts2)
    record_trace(_make_result(), [], opts2)
    traces = load_traces("echo hi", opts2)
    assert len(traces) == 2


def test_record_trace_prunes_to_keep_last(tmp_path):
    opts = _opts(tmp_path, keep_last=3)
    for _ in range(6):
        record_trace(_make_result(), [], opts)
    path = _trace_path(str(tmp_path), "echo hi")
    lines = [l for l in path.read_text().splitlines() if l.strip()]
    assert len(lines) == 3


def test_load_traces_missing_returns_empty(tmp_path):
    opts = _opts(tmp_path)
    assert load_traces("nonexistent", opts) == []
