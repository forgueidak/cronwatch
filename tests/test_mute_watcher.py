"""Tests for cronwatch/mute_watcher.py"""
import time

import pytest

from cronwatch.mute import mute_job, clear_mute_state
from cronwatch.mute_watcher import (
    MuteWatchOptions,
    check_mute,
    format_mute_notice,
)


@pytest.fixture()
def state_dir(tmp_path):
    return str(tmp_path / "mute")


def _opts(state_dir, enabled=True, job_name="test_job"):
    return MuteWatchOptions.from_dict({
        "job_name": job_name,
        "mute": {"enabled": enabled, "state_dir": state_dir},
    })


def test_defaults_when_key_missing():
    opts = MuteWatchOptions.from_dict({})
    assert opts.job_name == "default"
    assert opts.mute.enabled is False


def test_post_init_sets_default_job_name():
    opts = MuteWatchOptions()
    assert opts.job_name == "default"


def test_check_mute_disabled_returns_none(state_dir):
    mute_job(state_dir, "test_job", 3600)
    opts = _opts(state_dir, enabled=False)
    assert check_mute(opts) is None


def test_check_mute_active_returns_state(state_dir):
    mute_job(state_dir, "test_job", 3600, reason="ci")
    opts = _opts(state_dir, enabled=True)
    result = check_mute(opts)
    assert result is not None
    assert result.reason == "ci"


def test_check_mute_expired_returns_none(state_dir):
    from cronwatch.mute import MuteState, save_mute_state
    state = MuteState(muted_until=time.time() - 5, reason="old")
    save_mute_state(state_dir, "test_job", state)
    opts = _opts(state_dir, enabled=True)
    assert check_mute(opts) is None


def test_check_mute_no_state_returns_none(state_dir):
    opts = _opts(state_dir, enabled=True)
    assert check_mute(opts) is None


def test_format_mute_notice_includes_job_name(state_dir):
    from cronwatch.mute import MuteState
    state = MuteState(muted_until=time.time() + 120, reason="deploy")
    notice = format_mute_notice(state, "my_job")
    assert "my_job" in notice
    assert "deploy" in notice


def test_format_mute_notice_no_reason(state_dir):
    from cronwatch.mute import MuteState
    state = MuteState(muted_until=time.time() + 60, reason="")
    notice = format_mute_notice(state, "my_job")
    assert "Reason" not in notice
    assert "my_job" in notice
