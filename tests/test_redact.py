"""Tests for cronwatch.redact."""
import pytest
from cronwatch.redact import (
    RedactOptions,
    RedactResult,
    redact_text,
    apply_redaction,
)


# ---------------------------------------------------------------------------
# RedactOptions.from_dict
# ---------------------------------------------------------------------------

class TestRedactOptionsFromDict:
    def test_defaults(self):
        opts = RedactOptions.from_dict({})
        assert opts.enabled is False
        assert opts.patterns == []
        assert opts.placeholder == "[REDACTED]"

    def test_full(self):
        opts = RedactOptions.from_dict({
            "redact": {
                "enabled": True,
                "patterns": [r"secret=\S+", r"token=\S+"],
                "placeholder": "***",
            }
        })
        assert opts.enabled is True
        assert len(opts.patterns) == 2
        assert opts.placeholder == "***"

    def test_enabled_coerced_to_bool(self):
        opts = RedactOptions.from_dict({"redact": {"enabled": 1}})
        assert opts.enabled is True


# ---------------------------------------------------------------------------
# RedactResult helpers
# ---------------------------------------------------------------------------

class TestRedactResult:
    def test_ok_when_no_redactions(self):
        r = RedactResult(original="hello", redacted="hello", redaction_count=0)
        assert r.ok is True

    def test_not_ok_when_redactions_made(self):
        r = RedactResult(original="x", redacted="[REDACTED]", redaction_count=1)
        assert r.ok is False

    def test_summary_clean(self):
        r = RedactResult(original="x", redacted="x", redaction_count=0)
        assert "no sensitive" in r.summary()

    def test_summary_dirty(self):
        r = RedactResult(original="x", redacted="y", redaction_count=3)
        assert "3" in r.summary()


# ---------------------------------------------------------------------------
# redact_text
# ---------------------------------------------------------------------------

def test_disabled_returns_original():
    opts = RedactOptions(enabled=False, patterns=[r"secret=\S+"])
    result = redact_text("secret=abc123", opts)
    assert result.redacted == "secret=abc123"
    assert result.redaction_count == 0


def test_no_patterns_returns_original():
    opts = RedactOptions(enabled=True, patterns=[])
    result = redact_text("secret=abc123", opts)
    assert result.redacted == "secret=abc123"


def test_single_pattern_replaces_match():
    opts = RedactOptions(enabled=True, patterns=[r"secret=\S+"])
    result = redact_text("output secret=abc123 end", opts)
    assert "[REDACTED]" in result.redacted
    assert "abc123" not in result.redacted
    assert result.redaction_count == 1


def test_multiple_matches_counted():
    opts = RedactOptions(enabled=True, patterns=[r"token=\S+"])
    result = redact_text("token=aaa token=bbb", opts)
    assert result.redaction_count == 2


def test_invalid_pattern_skipped():
    opts = RedactOptions(enabled=True, patterns=[r"[invalid", r"ok=\S+"])
    result = redact_text("ok=value", opts)
    assert "[REDACTED]" in result.redacted


def test_custom_placeholder():
    opts = RedactOptions(enabled=True, patterns=[r"pw=\S+"], placeholder="<hidden>")
    result = redact_text("pw=hunter2", opts)
    assert "<hidden>" in result.redacted


# ---------------------------------------------------------------------------
# apply_redaction
# ---------------------------------------------------------------------------

def test_apply_redaction_both_streams():
    opts = RedactOptions(enabled=True, patterns=[r"key=\S+"])
    out, err = apply_redaction("key=abc", "key=xyz error", opts)
    assert "abc" not in out
    assert "xyz" not in err


def test_apply_redaction_disabled_passthrough():
    opts = RedactOptions(enabled=False, patterns=[r"key=\S+"])
    out, err = apply_redaction("key=abc", "key=xyz", opts)
    assert out == "key=abc"
    assert err == "key=xyz"
