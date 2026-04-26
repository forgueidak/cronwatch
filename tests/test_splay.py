"""Tests for cronwatch.splay."""
from __future__ import annotations

import pytest

from cronwatch.splay import (
    SplayOptions,
    SplayResult,
    apply_splay,
    compute_splay,
    format_splay_notice,
)


# ---------------------------------------------------------------------------
# SplayOptions.from_dict
# ---------------------------------------------------------------------------

class TestSplayOptionsFromDict:
    def test_defaults(self):
        opts = SplayOptions.from_dict({})
        assert opts.enabled is False
        assert opts.window_seconds == 60
        assert opts.seed is None

    def test_full(self):
        opts = SplayOptions.from_dict(
            {"splay": {"enabled": True, "window_seconds": 300, "seed": 7}}
        )
        assert opts.enabled is True
        assert opts.window_seconds == 300
        assert opts.seed == 7

    def test_enabled_coerced_to_bool(self):
        opts = SplayOptions.from_dict({"splay": {"enabled": 1}})
        assert opts.enabled is True

    def test_missing_nested_key_uses_defaults(self):
        opts = SplayOptions.from_dict({"splay": {}})
        assert opts.window_seconds == 60


# ---------------------------------------------------------------------------
# compute_splay
# ---------------------------------------------------------------------------

class TestComputeSplay:
    def test_disabled_returns_zero_delay(self):
        opts = SplayOptions(enabled=False, window_seconds=60)
        result = compute_splay(opts)
        assert result.delay_seconds == 0.0
        assert result.skipped is True
        assert result.ok() is True

    def test_enabled_delay_within_window(self):
        opts = SplayOptions(enabled=True, window_seconds=60, seed=42)
        result = compute_splay(opts)
        assert 0.0 <= result.delay_seconds <= 60.0
        assert result.skipped is False

    def test_deterministic_with_seed(self):
        opts = SplayOptions(enabled=True, window_seconds=100, seed=99)
        r1 = compute_splay(opts)
        r2 = compute_splay(opts)
        assert r1.delay_seconds == r2.delay_seconds

    def test_zero_window_gives_zero_delay(self):
        opts = SplayOptions(enabled=True, window_seconds=0, seed=1)
        result = compute_splay(opts)
        assert result.delay_seconds == 0.0


# ---------------------------------------------------------------------------
# apply_splay
# ---------------------------------------------------------------------------

def test_apply_splay_disabled_does_not_sleep():
    slept = []
    opts = SplayOptions(enabled=False, window_seconds=30)
    apply_splay(opts, _sleep=slept.append)
    assert slept == []


def test_apply_splay_enabled_calls_sleep():
    slept = []
    opts = SplayOptions(enabled=True, window_seconds=30, seed=5)
    result = apply_splay(opts, _sleep=slept.append)
    assert len(slept) == 1
    assert slept[0] == pytest.approx(result.delay_seconds)


# ---------------------------------------------------------------------------
# format_splay_notice
# ---------------------------------------------------------------------------

def test_format_notice_disabled_returns_empty():
    result = SplayResult(enabled=False, delay_seconds=0.0, skipped=True)
    assert format_splay_notice(result) == ""


def test_format_notice_enabled_contains_delay():
    result = SplayResult(enabled=True, delay_seconds=17.5)
    notice = format_splay_notice(result)
    assert "17.50" in notice
    assert "splay" in notice
