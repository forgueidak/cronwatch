"""Tests for cronwatch.stagger."""
import pytest
import random

from cronwatch.stagger import (
    StaggerOptions,
    StaggerResult,
    compute_stagger,
    apply_stagger,
    _deterministic_delay,
)


# ---------------------------------------------------------------------------
# StaggerOptions.from_dict
# ---------------------------------------------------------------------------

class TestStaggerOptionsFromDict:
    def test_defaults(self):
        opts = StaggerOptions.from_dict({})
        assert opts.enabled is False
        assert opts.max_delay_seconds == 60.0
        assert opts.seed == ""
        assert opts.deterministic is False

    def test_full(self):
        opts = StaggerOptions.from_dict({
            "stagger": {
                "enabled": True,
                "max_delay_seconds": 15.0,
                "seed": "host-1",
                "deterministic": True,
            }
        })
        assert opts.enabled is True
        assert opts.max_delay_seconds == 15.0
        assert opts.seed == "host-1"
        assert opts.deterministic is True

    def test_enabled_coerced_to_bool(self):
        opts = StaggerOptions.from_dict({"stagger": {"enabled": 1}})
        assert opts.enabled is True


# ---------------------------------------------------------------------------
# StaggerResult helpers
# ---------------------------------------------------------------------------

def test_result_ok_always_true():
    assert StaggerResult(delay_seconds=5.0).ok() is True
    assert StaggerResult(skipped=True, reason="disabled").ok() is True


def test_result_summary_skipped():
    r = StaggerResult(skipped=True, reason="disabled")
    assert "disabled" in r.summary()


def test_result_summary_with_delay():
    r = StaggerResult(delay_seconds=12.5)
    assert "12.5" in r.summary()


# ---------------------------------------------------------------------------
# _deterministic_delay
# ---------------------------------------------------------------------------

def test_deterministic_delay_in_range():
    d = _deterministic_delay("backup:host", 60.0)
    assert 0.0 <= d < 60.0


def test_deterministic_delay_stable():
    d1 = _deterministic_delay("myjob:", 30.0)
    d2 = _deterministic_delay("myjob:", 30.0)
    assert d1 == d2


def test_deterministic_delay_differs_for_different_seeds():
    d1 = _deterministic_delay("job:seed-A", 100.0)
    d2 = _deterministic_delay("job:seed-B", 100.0)
    assert d1 != d2


# ---------------------------------------------------------------------------
# compute_stagger
# ---------------------------------------------------------------------------

def test_compute_stagger_disabled():
    opts = StaggerOptions(enabled=False)
    r = compute_stagger(opts, "myjob")
    assert r.skipped is True
    assert r.delay_seconds == 0.0


def test_compute_stagger_zero_max_delay():
    opts = StaggerOptions(enabled=True, max_delay_seconds=0)
    r = compute_stagger(opts, "myjob")
    assert r.skipped is True


def test_compute_stagger_deterministic():
    opts = StaggerOptions(enabled=True, max_delay_seconds=60.0, deterministic=True, seed="s")
    r1 = compute_stagger(opts, "job")
    r2 = compute_stagger(opts, "job")
    assert r1.delay_seconds == r2.delay_seconds
    assert not r1.skipped


def test_compute_stagger_random_in_range():
    opts = StaggerOptions(enabled=True, max_delay_seconds=20.0, deterministic=False)
    rng = random.Random(42)
    r = compute_stagger(opts, "job", _random_source=rng)
    assert 0.0 <= r.delay_seconds <= 20.0
    assert not r.skipped


# ---------------------------------------------------------------------------
# apply_stagger
# ---------------------------------------------------------------------------

def test_apply_stagger_calls_sleep():
    slept = []
    opts = StaggerOptions(enabled=True, max_delay_seconds=10.0, deterministic=True)
    r = apply_stagger(opts, "myjob", _sleep=slept.append)
    assert len(slept) == 1
    assert slept[0] == r.delay_seconds


def test_apply_stagger_disabled_no_sleep():
    slept = []
    opts = StaggerOptions(enabled=False)
    apply_stagger(opts, "myjob", _sleep=slept.append)
    assert slept == []
