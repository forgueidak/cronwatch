"""Tests for cronwatch.pipeline."""
from __future__ import annotations

import pytest

from cronwatch.pipeline import (
    PipelineOptions,
    PipelineResult,
    PipelineStep,
    run_pipeline,
)
from cronwatch.runner import JobResult


def _make_result(success: bool = True) -> JobResult:
    return JobResult(
        command="echo hi",
        returncode=0 if success else 1,
        stdout="ok",
        stderr="",
        duration=0.1,
        timed_out=False,
    )


def _noop(result: JobResult) -> None:
    pass


def _boom(result: JobResult) -> None:
    raise RuntimeError("step failed")


# ---------------------------------------------------------------------------
# PipelineOptions
# ---------------------------------------------------------------------------

class TestPipelineOptions:
    def test_defaults(self):
        opts = PipelineOptions()
        assert opts.stop_on_error is False
        assert opts.steps == []

    def test_from_dict_stop_on_error(self):
        opts = PipelineOptions.from_dict({"stop_on_error": True})
        assert opts.stop_on_error is True

    def test_from_dict_empty(self):
        opts = PipelineOptions.from_dict({})
        assert opts.stop_on_error is False


# ---------------------------------------------------------------------------
# run_pipeline
# ---------------------------------------------------------------------------

class TestRunPipeline:
    def test_all_steps_run_on_success(self):
        calls = []
        step = PipelineStep(name="a", fn=lambda r: calls.append("a"))
        opts = PipelineOptions(steps=[step])
        pr = run_pipeline(_make_result(True), opts)
        assert "a" in pr.steps_run
        assert pr.ok

    def test_on_failure_only_skipped_for_success(self):
        step = PipelineStep(name="fail_hook", fn=_noop, on_failure_only=True)
        opts = PipelineOptions(steps=[step])
        pr = run_pipeline(_make_result(True), opts)
        assert "fail_hook" in pr.steps_skipped
        assert "fail_hook" not in pr.steps_run

    def test_on_failure_only_runs_for_failure(self):
        step = PipelineStep(name="fail_hook", fn=_noop, on_failure_only=True)
        opts = PipelineOptions(steps=[step])
        pr = run_pipeline(_make_result(False), opts)
        assert "fail_hook" in pr.steps_run

    def test_on_success_only_skipped_for_failure(self):
        step = PipelineStep(name="ok_hook", fn=_noop, on_success_only=True)
        opts = PipelineOptions(steps=[step])
        pr = run_pipeline(_make_result(False), opts)
        assert "ok_hook" in pr.steps_skipped

    def test_error_captured_in_result(self):
        step = PipelineStep(name="boom", fn=_boom)
        opts = PipelineOptions(steps=[step])
        pr = run_pipeline(_make_result(True), opts)
        assert "boom" in pr.errors
        assert "step failed" in pr.errors["boom"]
        assert not pr.ok

    def test_stop_on_error_halts_pipeline(self):
        calls = []
        s1 = PipelineStep(name="boom", fn=_boom)
        s2 = PipelineStep(name="after", fn=lambda r: calls.append("after"))
        opts = PipelineOptions(steps=[s1, s2], stop_on_error=True)
        pr = run_pipeline(_make_result(True), opts)
        assert "after" not in pr.steps_run
        assert calls == []

    def test_summary_text(self):
        step = PipelineStep(name="a", fn=_noop)
        opts = PipelineOptions(steps=[step])
        pr = run_pipeline(_make_result(True), opts)
        text = pr.summary()
        assert "ran=1" in text
        assert "skipped=0" in text
