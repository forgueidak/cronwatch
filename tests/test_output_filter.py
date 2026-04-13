"""Tests for cronwatch.output_filter."""

import pytest
from cronwatch.output_filter import (
    OutputFilterOptions,
    apply_output_filter,
    FilterResult,
)


def _opts(**kwargs) -> OutputFilterOptions:
    return OutputFilterOptions(**kwargs)


# ---------------------------------------------------------------------------
# OutputFilterOptions.from_dict
# ---------------------------------------------------------------------------

class TestOutputFilterOptions:
    def test_defaults(self):
        opts = OutputFilterOptions()
        assert opts.max_lines == 100
        assert opts.max_bytes == 8192
        assert opts.redact_patterns == []
        assert opts.include_pattern is None
        assert opts.exclude_pattern is None

    def test_from_dict_full(self):
        data = {
            "max_lines": 50,
            "max_bytes": 1024,
            "redact_patterns": ["password=\\S+"],
            "include_pattern": "ERROR",
            "exclude_pattern": "DEBUG",
        }
        opts = OutputFilterOptions.from_dict(data)
        assert opts.max_lines == 50
        assert opts.max_bytes == 1024
        assert opts.redact_patterns == ["password=\\S+"]
        assert opts.include_pattern == "ERROR"
        assert opts.exclude_pattern == "DEBUG"

    def test_from_dict_empty(self):
        opts = OutputFilterOptions.from_dict({})
        assert opts.max_lines == 100


# ---------------------------------------------------------------------------
# apply_output_filter
# ---------------------------------------------------------------------------

def test_plain_text_passes_through():
    result = apply_output_filter("hello world", _opts())
    assert result.text == "hello world"
    assert not result.truncated
    assert result.redacted_count == 0
    assert result.lines_removed == 0


def test_truncates_by_max_lines():
    text = "\n".join(f"line {i}" for i in range(200))
    result = apply_output_filter(text, _opts(max_lines=10))
    assert result.truncated
    assert len(result.text.splitlines()) == 10


def test_truncates_by_max_bytes():
    text = "a" * 2000
    result = apply_output_filter(text, _opts(max_bytes=100))
    assert result.truncated
    assert len(result.text.encode()) <= 100


def test_redact_single_pattern():
    text = "connecting with password=secret123 done"
    result = apply_output_filter(text, _opts(redact_patterns=[r"password=\S+"]))
    assert "secret123" not in result.text
    assert "[REDACTED]" in result.text
    assert result.redacted_count == 1


def test_redact_multiple_patterns():
    text = "token=abc123 and password=xyz"
    result = apply_output_filter(
        text, _opts(redact_patterns=[r"token=\S+", r"password=\S+"])
    )
    assert result.redacted_count == 2


def test_include_pattern_keeps_matching_lines():
    text = "INFO starting\nERROR boom\nINFO done"
    result = apply_output_filter(text, _opts(include_pattern="ERROR"))
    assert "ERROR boom" in result.text
    assert "INFO starting" not in result.text
    assert result.lines_removed == 2


def test_exclude_pattern_removes_matching_lines():
    text = "DEBUG verbose\nINFO useful\nDEBUG more noise"
    result = apply_output_filter(text, _opts(exclude_pattern="^DEBUG"))
    assert "INFO useful" in result.text
    assert "DEBUG" not in result.text
    assert result.lines_removed == 2


def test_filter_result_ok_when_clean():
    result = apply_output_filter("clean output", _opts())
    assert result.ok


def test_filter_result_not_ok_when_truncated():
    text = "\n".join(f"line {i}" for i in range(200))
    result = apply_output_filter(text, _opts(max_lines=5))
    assert not result.ok
