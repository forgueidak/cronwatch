"""Tests for cronwatch.roster and cronwatch.roster_watcher."""
import json
import pytest
from pathlib import Path

from cronwatch.roster import (
    RosterEntry,
    RosterOptions,
    _roster_path,
    register_job,
    load_job,
    list_jobs,
    deregister_job,
)
from cronwatch.roster_watcher import (
    RosterWatchOptions,
    ensure_registered,
    format_roster_notice,
)
from cronwatch.runner import JobResult


@pytest.fixture()
def roster_dir(tmp_path):
    return str(tmp_path / "roster")


def _make_result(command="echo hi", exit_code=0):
    return JobResult(
        command=command,
        exit_code=exit_code,
        stdout="",
        stderr="",
        duration=0.1,
        timed_out=False,
    )


# --- RosterEntry ---

def test_roster_entry_round_trip():
    e = RosterEntry(name="job1", command="/bin/job", schedule="@daily", tags=["a"])
    assert RosterEntry.from_dict(e.to_dict()) == e


def test_roster_entry_defaults():
    e = RosterEntry.from_dict({"name": "x", "command": "y"})
    assert e.enabled is True
    assert e.tags == []
    assert e.description == ""


# --- RosterOptions ---

def test_roster_options_defaults():
    opts = RosterOptions.from_dict({})
    assert opts.enabled is True
    assert "cronwatch" in opts.roster_dir


def test_roster_options_reads_nested_key():
    opts = RosterOptions.from_dict({"roster": {"enabled": False, "roster_dir": "/tmp/r"}})
    assert opts.enabled is False
    assert opts.roster_dir == "/tmp/r"


# --- register / load / list / deregister ---

def test_register_creates_file(roster_dir):
    e = RosterEntry(name="myjob", command="/bin/myjob")
    path = register_job(e, roster_dir)
    assert path.exists()


def test_load_job_returns_entry(roster_dir):
    e = RosterEntry(name="myjob", command="/bin/myjob", tags=["ops"])
    register_job(e, roster_dir)
    loaded = load_job("myjob", roster_dir)
    assert loaded is not None
    assert loaded.tags == ["ops"]


def test_load_job_missing_returns_none(roster_dir):
    assert load_job("ghost", roster_dir) is None


def test_list_jobs_empty_dir(roster_dir):
    assert list_jobs(roster_dir) == []


def test_list_jobs_returns_all(roster_dir):
    for n in ["a", "b", "c"]:
        register_job(RosterEntry(name=n, command=f"/bin/{n}"), roster_dir)
    jobs = list_jobs(roster_dir)
    assert len(jobs) == 3
    assert {j.name for j in jobs} == {"a", "b", "c"}


def test_deregister_removes_file(roster_dir):
    register_job(RosterEntry(name="gone", command="/bin/gone"), roster_dir)
    assert deregister_job("gone", roster_dir) is True
    assert load_job("gone", roster_dir) is None


def test_deregister_missing_returns_false(roster_dir):
    assert deregister_job("nope", roster_dir) is False


# --- roster_watcher ---

def test_ensure_registered_creates_entry(roster_dir):
    opts = RosterWatchOptions(enabled=True, roster_dir=roster_dir, tags=["ci"])
    result = _make_result(command="backup.sh")
    entry = ensure_registered(result, opts, job_name="backup")
    assert entry is not None
    assert entry.name == "backup"
    loaded = load_job("backup", roster_dir)
    assert loaded is not None


def test_ensure_registered_disabled_returns_none(roster_dir):
    opts = RosterWatchOptions(enabled=False, roster_dir=roster_dir)
    result = _make_result()
    assert ensure_registered(result, opts) is None


def test_ensure_registered_does_not_overwrite(roster_dir):
    opts = RosterWatchOptions(enabled=True, roster_dir=roster_dir, description="orig")
    result = _make_result(command="job.sh")
    ensure_registered(result, opts, job_name="job")
    opts2 = RosterWatchOptions(enabled=True, roster_dir=roster_dir, description="new")
    ensure_registered(result, opts2, job_name="job")
    loaded = load_job("job", roster_dir)
    assert loaded.description == "orig"


def test_format_roster_notice_with_tags():
    e = RosterEntry(name="j", command="c", schedule="@daily", tags=["x", "y"])
    msg = format_roster_notice(e)
    assert "j" in msg
    assert "x, y" in msg


def test_format_roster_notice_no_tags():
    e = RosterEntry(name="j", command="c")
    msg = format_roster_notice(e)
    assert "none" in msg
