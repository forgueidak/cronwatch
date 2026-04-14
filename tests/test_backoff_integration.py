"""Integration-style tests: backoff used with RetryOptions."""
import random
import pytest
from cronwatch.backoff import BackoffOptions, compute_delay


def _simulate_delays(opts: BackoffOptions, attempts: int, seed: int = 0) -> list:
    """Return a list of delays for *attempts* retries."""
    rng = random.Random(seed)
    return [compute_delay(opts, attempt=i + 1, _random=rng) for i in range(attempts)]


class TestBackoffSequence:
    def test_delays_are_non_decreasing_without_jitter(self):
        opts = BackoffOptions.from_dict(
            {"enabled": True, "base_delay": 1.0, "multiplier": 2.0,
             "max_delay": 64.0, "jitter": False}
        )
        results = _simulate_delays(opts, attempts=7)
        delays = [r.delay for r in results]
        assert delays == sorted(delays)

    def test_all_delays_within_max(self):
        opts = BackoffOptions.from_dict(
            {"enabled": True, "base_delay": 5.0, "multiplier": 3.0,
             "max_delay": 30.0, "jitter": False}
        )
        results = _simulate_delays(opts, attempts=10)
        for r in results:
            assert r.delay <= opts.max_delay

    def test_capped_flag_set_correctly(self):
        opts = BackoffOptions.from_dict(
            {"enabled": True, "base_delay": 10.0, "multiplier": 2.0,
             "max_delay": 20.0, "jitter": False}
        )
        results = _simulate_delays(opts, attempts=5)
        # attempt 1: 10 (not capped), attempt 2: 20 (capped), rest also capped
        assert results[0].capped is False
        for r in results[1:]:
            assert r.capped is True

    def test_disabled_all_zeros(self):
        opts = BackoffOptions.from_dict({"enabled": False})
        results = _simulate_delays(opts, attempts=5)
        assert all(r.delay == 0.0 for r in results)

    def test_attempt_numbers_correct(self):
        opts = BackoffOptions.from_dict({"enabled": True, "jitter": False})
        results = _simulate_delays(opts, attempts=4)
        for i, r in enumerate(results):
            assert r.attempt == i + 1
