"""Tests for cronwatch.backoff."""
import random
import pytest
from cronwatch.backoff import BackoffOptions, BackoffResult, compute_delay


# ---------------------------------------------------------------------------
# BackoffOptions.from_dict
# ---------------------------------------------------------------------------

class TestBackoffOptionsFromDict:
    def test_defaults(self):
        opts = BackoffOptions.from_dict({})
        assert opts.enabled is False
        assert opts.base_delay == 1.0
        assert opts.multiplier == 2.0
        assert opts.max_delay == 60.0
        assert opts.jitter is True
        assert opts.jitter_range == 0.5

    def test_full(self):
        opts = BackoffOptions.from_dict(
            {"enabled": True, "base_delay": 3.0, "multiplier": 3.0,
             "max_delay": 30.0, "jitter": False, "jitter_range": 0.1}
        )
        assert opts.enabled is True
        assert opts.base_delay == 3.0
        assert opts.multiplier == 3.0
        assert opts.max_delay == 30.0
        assert opts.jitter is False
        assert opts.jitter_range == 0.1

    def test_enabled_coerced_to_bool(self):
        opts = BackoffOptions.from_dict({"enabled": 1})
        assert opts.enabled is True


# ---------------------------------------------------------------------------
# BackoffResult helpers
# ---------------------------------------------------------------------------

class TestBackoffResult:
    def test_ok_always_true_for_non_negative_delay(self):
        r = BackoffResult(attempt=1, delay=5.0, capped=False)
        assert r.ok() is True

    def test_summary_contains_attempt_and_delay(self):
        r = BackoffResult(attempt=2, delay=4.0, capped=False)
        assert "attempt=2" in r.summary()
        assert "4.00s" in r.summary()

    def test_summary_shows_capped(self):
        r = BackoffResult(attempt=5, delay=60.0, capped=True)
        assert "capped" in r.summary()


# ---------------------------------------------------------------------------
# compute_delay
# ---------------------------------------------------------------------------

class TestComputeDelay:
    _rng = random.Random(42)

    def _opts(self, **kw) -> BackoffOptions:
        base = {"enabled": True, "jitter": False}
        base.update(kw)
        return BackoffOptions.from_dict(base)

    def test_disabled_returns_zero(self):
        opts = BackoffOptions.from_dict({"enabled": False})
        r = compute_delay(opts, attempt=3)
        assert r.delay == 0.0

    def test_attempt_zero_returns_zero(self):
        opts = self._opts()
        r = compute_delay(opts, attempt=0)
        assert r.delay == 0.0

    def test_first_attempt_equals_base_delay(self):
        opts = self._opts(base_delay=5.0, multiplier=2.0)
        r = compute_delay(opts, attempt=1)
        assert r.delay == pytest.approx(5.0)

    def test_second_attempt_doubles(self):
        opts = self._opts(base_delay=4.0, multiplier=2.0)
        r = compute_delay(opts, attempt=2)
        assert r.delay == pytest.approx(8.0)

    def test_delay_capped_at_max(self):
        opts = self._opts(base_delay=10.0, multiplier=10.0, max_delay=50.0)
        r = compute_delay(opts, attempt=3)
        assert r.delay == pytest.approx(50.0)
        assert r.capped is True

    def test_jitter_changes_value(self):
        opts = BackoffOptions.from_dict(
            {"enabled": True, "base_delay": 10.0, "multiplier": 1.0,
             "max_delay": 120.0, "jitter": True, "jitter_range": 0.5}
        )
        rng = random.Random(0)
        r = compute_delay(opts, attempt=1, _random=rng)
        assert r.delay != pytest.approx(10.0)

    def test_jitter_never_negative(self):
        opts = BackoffOptions.from_dict(
            {"enabled": True, "base_delay": 0.01, "multiplier": 1.0,
             "max_delay": 120.0, "jitter": True, "jitter_range": 1.0}
        )
        rng = random.Random(99)
        for _ in range(50):
            r = compute_delay(opts, attempt=1, _random=rng)
            assert r.delay >= 0.0
