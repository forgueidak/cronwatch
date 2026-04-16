"""Tests for cronwatch.profile."""
import json
from pathlib import Path

import pytest

from cronwatch.profile import (
    ProfileOptions,
    _profile_path,
    check_profile,
    load_durations,
    record_duration,
)
from cronwatch.runner import JobResult


def _make_result(success=True, duration=1.0, command="/bin/job"):
    return JobResult(
        command=command,
        returncode=0 if success else 1,
        stdout="ok",
        stderr="",
        duration=duration,
        timed_out=False,
    )


@pytest.fixture()
def prof_dir(tmp_path):
    return tmp_path / "profiles"


def _opts(prof_dir, window=5, factor=2.0):
    return ProfileOptions(enabled=True, directory=prof_dir, window=window, warn_factor=factor)


class TestProfileOptionsFromDict:
    def test_defaults(self):
        o = ProfileOptions.from_dict({})
        assert o.enabled is False
        assert o.window == 20
        assert o.warn_factor == 2.0

    def test_full(self):
        o = ProfileOptions.from_dict({"enabled": True, "window": 10, "warn_factor": 3.0})
        assert o.enabled is True
        assert o.window == 10
        assert o.warn_factor == 3.0


def test_profile_path_sanitizes(tmp_path):
    p = _profile_path(tmp_path, "/usr/bin/my job")
    assert "/" not in p.name
    assert " " not in p.name


def test_record_and_load_durations(prof_dir):
    record_duration(prof_dir, "cmd", 1.5)
    record_duration(prof_dir, "cmd", 2.0)
    durations = load_durations(prof_dir, "cmd", window=10)
    assert durations == [1.5, 2.0]


def test_load_durations_respects_window(prof_dir):
    for i in range(10):
        record_duration(prof_dir, "cmd", float(i))
    durations = load_durations(prof_dir, "cmd", window=3)
    assert len(durations) == 3
    assert durations == [7.0, 8.0, 9.0]


def test_check_profile_disabled_returns_none(prof_dir):
    opts = ProfileOptions(enabled=False, directory=prof_dir)
    assert check_profile(_make_result(), opts) is None


def test_check_profile_failed_job_returns_none(prof_dir):
    opts = _opts(prof_dir)
    assert check_profile(_make_result(success=False), opts) is None


def test_check_profile_not_enough_history(prof_dir):
    opts = _opts(prof_dir)
    r = check_profile(_make_result(duration=5.0), opts)
    assert r is not None
    assert r.slow is False
    assert r.mean is None


def test_check_profile_normal_duration(prof_dir):
    opts = _opts(prof_dir, factor=2.0)
    for _ in range(5):
        record_duration(prof_dir, "/bin/job", 1.0)
    r = check_profile(_make_result(duration=1.5), opts)
    assert r is not None
    assert r.slow is False
    assert r.ok() is True


def test_check_profile_slow_duration(prof_dir):
    opts = _opts(prof_dir, factor=2.0)
    for _ in range(5):
        record_duration(prof_dir, "/bin/job", 1.0)
    r = check_profile(_make_result(duration=10.0), opts)
    assert r is not None
    assert r.slow is True
    assert r.ok() is False
    assert "exceeds" in r.message
