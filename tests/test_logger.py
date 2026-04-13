import json
import os
import time
import tempfile
import pytest

from cronwatch.runner import JobResult
from cronwatch.logger import write_job_log


@pytest.fixture()
def tmp_log_dir(tmp_path):
    return str(tmp_path / "cronwatch_logs")


def _make_result(exit_code=0, command="echo test") -> JobResult:
    return JobResult(
        command=command,
        exit_code=exit_code,
        stdout="test output",
        stderr="" if exit_code == 0 else "something went wrong",
        duration_seconds=0.123,
        started_at=time.time(),
    )


def test_write_job_log_creates_file(tmp_log_dir):
    result = _make_result()
    log_path = write_job_log(result, log_dir=tmp_log_dir)
    assert os.path.isfile(log_path)
    assert log_path.endswith("jobs.jsonl")


def test_write_job_log_valid_json(tmp_log_dir):
    result = _make_result()
    log_path = write_job_log(result, log_dir=tmp_log_dir)
    with open(log_path) as fh:
        entry = json.loads(fh.readline())
    assert entry["command"] == "echo test"
    assert entry["exit_code"] == 0
    assert entry["success"] is True
    assert "timestamp" in entry
    assert "duration_seconds" in entry


def test_write_job_log_failure_entry(tmp_log_dir):
    result = _make_result(exit_code=1)
    log_path = write_job_log(result, log_dir=tmp_log_dir)
    with open(log_path) as fh:
        entry = json.loads(fh.readline())
    assert entry["success"] is False
    assert entry["exit_code"] == 1
    assert "something went wrong" in entry["stderr"]


def test_write_job_log_appends_multiple(tmp_log_dir):
    write_job_log(_make_result(command="job1"), log_dir=tmp_log_dir)
    write_job_log(_make_result(command="job2"), log_dir=tmp_log_dir)
    log_path = os.path.join(tmp_log_dir, "jobs.jsonl")
    with open(log_path) as fh:
        lines = fh.readlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["command"] == "job1"
    assert json.loads(lines[1])["command"] == "job2"
