"""Tests for cronwatch.prefix."""
import pytest
from cronwatch.prefix import PrefixOptions, PrefixResult, apply_prefix, _build_prefix


class TestPrefixOptionsFromDict:
    def test_defaults(self):
        opts = PrefixOptions.from_dict({})
        assert opts.enabled is False
        assert opts.template == "[{job}]"
        assert opts.include_timestamp is False
        assert opts.timestamp_format == "%Y-%m-%dT%H:%M:%S"

    def test_full(self):
        opts = PrefixOptions.from_dict({
            "enabled": True,
            "template": "({job})",
            "include_timestamp": True,
            "timestamp_format": "%H:%M",
        })
        assert opts.enabled is True
        assert opts.template == "({job})"
        assert opts.include_timestamp is True
        assert opts.timestamp_format == "%H:%M"

    def test_enabled_coerced(self):
        opts = PrefixOptions.from_dict({"enabled": 1})
        assert opts.enabled is True


class TestBuildPrefix:
    def test_simple_prefix(self):
        opts = PrefixOptions(enabled=True, template="[{job}]")
        result = _build_prefix(opts, "backup")
        assert result == "[backup]"

    def test_prefix_with_timestamp(self):
        opts = PrefixOptions(enabled=True, template="[{job}]", include_timestamp=True)
        result = _build_prefix(opts, "backup", ts="2024-01-01T00:00:00")
        assert result == "2024-01-01T00:00:00 [backup]"

    def test_prefix_no_ts_when_not_included(self):
        opts = PrefixOptions(enabled=True, template="[{job}]", include_timestamp=False)
        result = _build_prefix(opts, "myjob", ts="ignored")
        assert result == "[myjob]"


class TestApplyPrefix:
    def test_disabled_returns_original(self):
        opts = PrefixOptions(enabled=False)
        r = apply_prefix("hello\nworld", "myjob", opts)
        assert r.prefixed == "hello\nworld"
        assert r.lines_processed == 0

    def test_empty_output_returns_as_is(self):
        opts = PrefixOptions(enabled=True)
        r = apply_prefix("", "myjob", opts)
        assert r.prefixed == ""
        assert r.lines_processed == 0

    def test_prefixes_each_line(self):
        opts = PrefixOptions(enabled=True, template="[{job}]", include_timestamp=False)
        r = apply_prefix("line1\nline2", "backup", opts)
        assert r.prefixed == "[backup] line1\n[backup] line2"
        assert r.lines_processed == 2

    def test_skips_blank_lines(self):
        opts = PrefixOptions(enabled=True, template="[{job}]", include_timestamp=False)
        r = apply_prefix("line1\n\nline3", "job", opts)
        lines = r.prefixed.splitlines()
        assert lines[0] == "[job] line1"
        assert lines[1] == ""
        assert lines[2] == "[job] line3"
        assert r.lines_processed == 2

    def test_result_ok_always_true(self):
        opts = PrefixOptions(enabled=True, template="[{job}]")
        r = apply_prefix("out", "j", opts)
        assert r.ok is True

    def test_summary_message(self):
        opts = PrefixOptions(enabled=True, template="[{job}]")
        r = apply_prefix("a\nb", "myjob", opts)
        assert "myjob" in r.summary()
        assert "2" in r.summary()
