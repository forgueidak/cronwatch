"""Tests for cronwatch/pause_watcher.py"""
from __future__ import annotations

from pathlib import Path

import pytest

from cronwatch.pause import pause_job, resume_job
from cronwatch.pause_watcher import (
    PauseWatchOptions,
    check_pause,
    format_pause_notice,
)


@pytest.fixture()
def state_dir(tmp_path: Path) -> str:
    return str(tmp_path / "pause")


def _opts(state_dir: str) -> PauseWatchOptions:
    return PauseWatchOptions(enabled=True, state_dir=state_dir)


def test_defaults_when_key_missing() -> None:
    opts = PauseWatchOptions.from_dict({})
    assert opts.enabled is True


def test_reads_nested_key() -> None:
    opts = PauseWatchOptions.from_dict({"pause": {"enabled": False}})
    assert opts.enabled is False


def test_post_init_sets_default_state_dir() -> None:
    opts = PauseWatchOptions(enabled=True, state_dir="")
    assert opts._opts.state_dir != ""


def test_check_pause_returns_false_when_not_paused(state_dir: str) -> None:
    assert check_pause("myjob", _opts(state_dir)) is False


def test_check_pause_returns_true_when_paused(state_dir: str) -> None:
    pause_job("myjob", state_dir=state_dir)
    assert check_pause("myjob", _opts(state_dir)) is True


def test_check_pause_returns_false_when_disabled(state_dir: str) -> None:
    pause_job("myjob", state_dir=state_dir)
    opts = PauseWatchOptions(enabled=False, state_dir=state_dir)
    assert check_pause("myjob", opts) is False


def test_check_pause_clears_after_resume(state_dir: str) -> None:
    pause_job("myjob", state_dir=state_dir)
    resume_job("myjob", state_dir=state_dir)
    assert check_pause("myjob", _opts(state_dir)) is False


def test_format_pause_notice_includes_job_name(state_dir: str) -> None:
    pause_job("myjob", reason="scheduled downtime", state_dir=state_dir)
    notice = format_pause_notice("myjob", _opts(state_dir))
    assert "myjob" in notice
    assert "scheduled downtime" in notice


def test_format_pause_notice_includes_resume_after(state_dir: str) -> None:
    pause_job("myjob", resume_after="2099-01-01T00:00:00+00:00", state_dir=state_dir)
    notice = format_pause_notice("myjob", _opts(state_dir))
    assert "2099-01-01" in notice


def test_format_pause_notice_no_reason(state_dir: str) -> None:
    pause_job("myjob", state_dir=state_dir)
    notice = format_pause_notice("myjob", _opts(state_dir))
    assert "myjob" in notice
