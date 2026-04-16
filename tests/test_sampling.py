"""Tests for cronwatch.sampling."""
import random
import pytest
from cronwatch.sampling import SamplingOptions, SamplingResult, should_sample


class TestSamplingOptionsFromDict:
    def test_defaults(self):
        opts = SamplingOptions.from_dict({})
        assert opts.enabled is False
        assert opts.rate == 1.0
        assert opts.seed is None

    def test_full(self):
        opts = SamplingOptions.from_dict({"enabled": True, "rate": 0.5, "seed": 7})
        assert opts.enabled is True
        assert opts.rate == 0.5
        assert opts.seed == 7

    def test_enabled_coerced(self):
        opts = SamplingOptions.from_dict({"enabled": 1})
        assert opts.enabled is True

    def test_rate_coerced_to_float(self):
        opts = SamplingOptions.from_dict({"rate": "0.3"})
        assert isinstance(opts.rate, float)


class TestSamplingResult:
    def test_ok_when_sampled(self):
        r = SamplingResult(enabled=True, rate=1.0, sampled=True)
        assert r.ok() is True

    def test_not_ok_when_skipped(self):
        r = SamplingResult(enabled=True, rate=0.0, sampled=False)
        assert r.ok() is False

    def test_summary_disabled(self):
        r = SamplingResult(enabled=False, rate=1.0, sampled=True)
        assert "disabled" in r.summary()

    def test_summary_sampled(self):
        r = SamplingResult(enabled=True, rate=0.5, sampled=True)
        assert "sampled" in r.summary()

    def test_summary_skipped(self):
        r = SamplingResult(enabled=True, rate=0.5, sampled=False)
        assert "skipped" in r.summary()


class TestShouldSample:
    def test_disabled_always_proceeds(self):
        opts = SamplingOptions(enabled=False, rate=0.0)
        result = should_sample(opts)
        assert result.sampled is True
        assert result.enabled is False

    def test_rate_one_always_samples(self):
        opts = SamplingOptions(enabled=True, rate=1.0, seed=0)
        for _ in range(20):
            assert should_sample(opts).sampled is True

    def test_rate_zero_never_samples(self):
        opts = SamplingOptions(enabled=True, rate=0.0, seed=0)
        for _ in range(20):
            assert should_sample(opts).sampled is False

    def test_seed_reproducible(self):
        opts = SamplingOptions(enabled=True, rate=0.5, seed=42)
        results = [should_sample(opts).sampled for _ in range(10)]
        results2 = [should_sample(opts).sampled for _ in range(10)]
        assert results == results2

    def test_custom_rng(self):
        opts = SamplingOptions(enabled=True, rate=0.5)
        rng = random.Random(99)
        result = should_sample(opts, rng=rng)
        assert isinstance(result.sampled, bool)

    def test_rate_clamped_above_one(self):
        opts = SamplingOptions(enabled=True, rate=5.0, seed=1)
        assert should_sample(opts).sampled is True

    def test_rate_clamped_below_zero(self):
        opts = SamplingOptions(enabled=True, rate=-1.0, seed=1)
        assert should_sample(opts).sampled is False
