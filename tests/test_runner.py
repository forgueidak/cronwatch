import time
import pytest
from cronwatch.runner import run_job, JobResult


def test_run_job_success():
    result = run_job("echo hello")
    assert isinstance(result, JobResult)
    assert result.exit_code == 0
    assert result.success is True
    assert "hello" in result.stdout
    assert result.stderr == ""
    assert result.duration_seconds >= 0


def test_run_job_failure():
    result = run_job("exit 42", shell=True)
    assert result.exit_code == 42
    assert result.success is False


def test_run_job_stderr_captured():
    result = run_job("echo error >&2", shell=True)
    assert "error" in result.stderr


def test_run_job_timeout():
    result = run_job("sleep 10", timeout=1)
    assert result.exit_code == -1
    assert result.success is False
    assert "TimeoutExpired" in result.stderr
    assert result.duration_seconds < 5


def test_job_result_summary_success():
    result = JobResult(
        command="echo hi",
        exit_code=0,
        stdout="hi",
        stderr="",
        duration_seconds=0.05,
        started_at=time.time(),
    )
    summary = result.summary()
    assert "SUCCESS" in summary
    assert "echo hi" in summary
    assert "exit_code=0" in summary


def test_job_result_summary_failure():
    result = JobResult(
        command="false",
        exit_code=1,
        stdout="",
        stderr="",
        duration_seconds=0.01,
        started_at=time.time(),
    )
    assert "FAILURE" in result.summary()
    assert result.success is False
