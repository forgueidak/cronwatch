"""Tests for cronwatch.profile_watcher."""
from pathlib import Path

import pytest

from cronwatch.profile import ProfileOptions
from cronwatch.profile_watcher import ProfileWatchOptions, format_slow_notice, watch_profile
from cronwatch.runner import JobResult


def _make_result(success=True, duration=1.0, command="/bin/job"):
    return JobResult(
        command=command,
        returncode=0 if success else 1,
        stdout="",
        stderr="",
        duration=duration,
        timed_out=False,
    )


@pytest.fixture()
def prof_dir(tmp_path):
    return tmp_path / "profiles"


def _opts(prof_dir, enabled=True, factor=2.0, notify=True):
    return ProfileWatchOptions(
        profile=ProfileOptions(enabled=enabled, directory=prof_dir, window=5, warn_factor=factor),
        notify_on_slow=notify,
    )


class TestProfileWatchOptionsFromDict:
    def test_defaults(self):
        o = ProfileWatchOptions.from_dict({})
        assert o.notify_on_slow is True
        assert o.profile.enabled is False

    def test_full(self, tmp_path):
        o = ProfileWatchOptions.from_dict({
            "profile": {"enabled": True, "window": 10},
            "notify_on_slow": False,
        })
        assert o.notify_on_slow is False
        assert o.profile.window == 10


def test_watch_profile_disabled_returns_none(prof_dir):
    opts = _opts(prof_dir, enabled=False)
    assert watch_profile(_make_result(), opts) is None


def test_watch_profile_failed_job_returns_none(prof_dir):
    opts = _opts(prof_dir)
    assert watch_profile(_make_result(success=False), opts) is None


def test_watch_profile_no_history_returns_not_slow(prof_dir):
    opts = _opts(prof_dir)
    r = watch_profile(_make_result(duration=99.0), opts)
    assert r is not None
    assert r.slow is False


def test_watch_profile_slow_detected(prof_dir):
    from cronwatch.profile import record_duration
    for _ in range(5):
        record_duration(prof_dir, "/bin/job", 1.0)
    opts = _opts(prof_dir, factor=2.0)
    r = watch_profile(_make_result(duration=10.0), opts)
    assert r is not None
    assert r.slow is True


def test_format_slow_notice_contains_command(prof_dir):
    from cronwatch.profile import record_duration, ProfileResult
    pr = ProfileResult(slow=True, duration=10.0, mean=1.0, threshold=2.0,
                       message="Duration 10.00s exceeds threshold 2.00s")
    result = _make_result(command="/bin/myjob")
    notice = format_slow_notice(result, pr)
    assert "/bin/myjob" in notice
    assert "Slow job" in notice
    assert "Mean" in notice
