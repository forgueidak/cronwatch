"""Tests for cronwatch.output_capture."""
import pytest
from cronwatch.output_capture import (
    OutputCaptureOptions,
    CaptureResult,
    _truncate,
    apply_capture_options,
)


class TestOutputCaptureOptions:
    def test_defaults(self):
        opts = OutputCaptureOptions()
        assert opts.enabled is True
        assert opts.max_bytes == 64 * 1024
        assert opts.max_lines == 500
        assert opts.capture_stdout is True
        assert opts.capture_stderr is True

    def test_from_dict_full(self):
        opts = OutputCaptureOptions.from_dict({
            "enabled": False,
            "max_bytes": 1024,
            "max_lines": 50,
            "truncation_marker": "[cut]",
            "capture_stdout": False,
            "capture_stderr": True,
        })
        assert opts.enabled is False
        assert opts.max_bytes == 1024
        assert opts.max_lines == 50
        assert opts.truncation_marker == "[cut]"
        assert opts.capture_stdout is False
        assert opts.capture_stderr is True

    def test_from_dict_empty_uses_defaults(self):
        opts = OutputCaptureOptions.from_dict({})
        assert opts.enabled is True
        assert opts.max_lines == 500


class TestCaptureResult:
    def test_ok_when_not_truncated(self):
        r = CaptureResult(stdout="hello", stderr="")
        assert r.ok is True

    def test_not_ok_when_stdout_truncated(self):
        r = CaptureResult(stdout="x", stdout_truncated=True)
        assert r.ok is False

    def test_summary_no_truncation(self):
        r = CaptureResult()
        assert r.summary() == "output within limits"

    def test_summary_both_truncated(self):
        r = CaptureResult(stdout_truncated=True, stderr_truncated=True)
        assert "stdout" in r.summary()
        assert "stderr" in r.summary()


class TestTruncate:
    def test_empty_string_unchanged(self):
        result, truncated = _truncate("", 100, 10, "[cut]")
        assert resultn        assert truncated is False

    def test_within_limits_unchanged(self):
        text = "line1\nline2\n"
        result, truncated = _truncate(text, 1024, 100, "[cut]")
        assert result == text
        assert truncated is False

    def test_exceeds_line_limit(self):
        text = "\n".join(f"line {i}" for i in range(20)) + "\n"
        result, truncated = _truncate(text, 99999, 5, "[cut]")
        assert truncated is True
        assert "[cut]" in result
        assert result.count("\n") <= 6  # 5 lines + marker line

    def test_exceeds_byte_limit(self):
        text = "a" * 200
        result, truncated = _truncate(text, 50, 9999, "[cut]")
        assert truncated is True
        assert "[cut]" in result
        assert len(result.encode()) <= 60  # 50 bytes + marker


class TestApplyCaptureOptions:
    def test_disabled_returns_raw(self):
        opts = OutputCaptureOptions(enabled=False)
        r = apply_capture_options("out", "err", opts)
        assert r.stdout == "out"
        assert r.stderr == "err"
        assert r.ok is True

    def test_capture_stdout_false_blanks_stdout(self):
        opts = OutputCaptureOptions(capture_stdout=False)
        r = apply_capture_options("important stdout", "err", opts)
        assert r.stdout == ""
        assert r.stderr == "err"

    def test_truncates_long_stderr(self):
        opts = OutputCaptureOptions(max_lines=3, truncation_marker="[trunc]")
        stderr = "\n".join(f"err {i}" for i in range(10)) + "\n"
        r = apply_capture_options("", stderr, opts)
        assert r.stderr_truncated is True
        assert "[trunc]" in r.stderr

    def test_no_opts_uses_defaults(self):
        r = apply_capture_options("hello", "world")
        assert r.stdout == "hello"
        assert r.stderr == "world"
        assert r.ok is True
