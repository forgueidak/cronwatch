"""Tests for cronwatch.jitter."""

from __future__ import annotations

import pytest

from cronwatch.jitter import JitterOptions, JitterResult, apply_jitter


# ---------------------------------------------------------------------------
# JitterOptions.from_dict
# ---------------------------------------------------------------------------

class TestJitterOptionsFromDict:
    def test_defaults(self):
        opts = JitterOptions.from_dict({})
        assert opts.enabled is False
        assert opts.min_seconds == 0.0
        assert opts.max_seconds == 30.0
        assert opts.seed is None

    def test_full(self):
        opts = JitterOptions.from_dict(
            {"enabled": True, "min_seconds": 5.0, "max_seconds": 15.0, "seed": 42}
        )
        assert opts.enabled is True
        assert opts.min_seconds == 5.0
        assert opts.max_seconds == 15.0
        assert opts.seed == 42

    def test_enabled_coerced_to_bool(self):
        opts = JitterOptions.from_dict({"enabled": 1})
        assert opts.enabled is True


# ---------------------------------------------------------------------------
# JitterResult
# ---------------------------------------------------------------------------

class TestJitterResult:
    def test_ok_always_true(self):
        assert JitterResult(skipped=True, delay_seconds=0.0).ok is True
        assert JitterResult(skipped=False, delay_seconds=5.0).ok is True

    def test_summary_skipped(self):
        r = JitterResult(skipped=True, delay_seconds=0.0)
        assert "disabled" in r.summary()

    def test_summary_delayed(self):
        r = JitterResult(skipped=False, delay_seconds=7.5)
        assert "7.50" in r.summary()


# ---------------------------------------------------------------------------
# apply_jitter
# ---------------------------------------------------------------------------

def test_apply_jitter_disabled_skips():
    slept = []
    opts = JitterOptions(enabled=False)
    result = apply_jitter(opts, _sleep=slept.append)
    assert result.skipped is True
    assert result.delay_seconds == 0.0
    assert slept == []


def test_apply_jitter_enabled_sleeps():
    slept = []
    opts = JitterOptions(enabled=True, min_seconds=1.0, max_seconds=5.0, seed=0)
    result = apply_jitter(opts, _sleep=slept.append)
    assert result.skipped is False
    assert 1.0 <= result.delay_seconds <= 5.0
    assert len(slept) == 1
    assert slept[0] == pytest.approx(result.delay_seconds)


def test_apply_jitter_deterministic_with_seed():
    opts = JitterOptions(enabled=True, min_seconds=0.0, max_seconds=100.0, seed=99)
    r1 = apply_jitter(opts, _sleep=lambda _: None)
    r2 = apply_jitter(opts, _sleep=lambda _: None)
    assert r1.delay_seconds == r2.delay_seconds


def test_apply_jitter_respects_min_max():
    opts = JitterOptions(enabled=True, min_seconds=10.0, max_seconds=10.0, seed=7)
    result = apply_jitter(opts, _sleep=lambda _: None)
    assert result.delay_seconds == pytest.approx(10.0)
