"""Tests for cronwatch.env_check."""

import os
import pytest

from cronwatch.env_check import (
    EnvCheckOptions,
    EnvCheckResult,
    check_env,
    env_check_from_config,
)


# ---------------------------------------------------------------------------
# check_env — required variables
# ---------------------------------------------------------------------------

def test_check_env_no_rules_passes(monkeypatch):
    result = check_env(EnvCheckOptions())
    assert result.ok


def test_check_env_required_present(monkeypatch):
    monkeypatch.setenv("MY_VAR", "hello")
    result = check_env(EnvCheckOptions(required=["MY_VAR"]))
    assert result.ok
    assert result.missing == []


def test_check_env_required_missing(monkeypatch):
    monkeypatch.delenv("MISSING_VAR", raising=False)
    result = check_env(EnvCheckOptions(required=["MISSING_VAR"]))
    assert not result.ok
    assert "MISSING_VAR" in result.missing
    assert result.passed is False


# ---------------------------------------------------------------------------
# check_env — expected values
# ---------------------------------------------------------------------------

def test_check_env_expected_matches(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    result = check_env(EnvCheckOptions(expected={"ENV": "production"}))
    assert result.ok
    assert result.mismatched == {}


def test_check_env_expected_mismatch(monkeypatch):
    monkeypatch.setenv("ENV", "staging")
    result = check_env(EnvCheckOptions(expected={"ENV": "production"}))
    assert not result.ok
    assert "ENV" in result.mismatched
    assert result.mismatched["ENV"] == ("production", "staging")


def test_check_env_expected_missing_var(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)
    result = check_env(EnvCheckOptions(expected={"ENV": "production"}))
    assert not result.ok
    assert "ENV" in result.missing


# ---------------------------------------------------------------------------
# warn_only mode
# ---------------------------------------------------------------------------

def test_warn_only_still_records_issues(monkeypatch):
    monkeypatch.delenv("REQUIRED_VAR", raising=False)
    result = check_env(EnvCheckOptions(required=["REQUIRED_VAR"], warn_only=True))
    assert "REQUIRED_VAR" in result.missing
    assert result.passed is True  # warn_only keeps passed=True
    assert not result.ok  # ok checks missing/mismatched too


# ---------------------------------------------------------------------------
# summary text
# ---------------------------------------------------------------------------

def test_summary_all_passed():
    result = EnvCheckResult()
    assert result.summary() == "All environment checks passed."


def test_summary_missing_vars():
    result = EnvCheckResult(missing=["FOO", "BAR"])
    summary = result.summary()
    assert "FOO" in summary
    assert "BAR" in summary


def test_summary_mismatched_vars():
    result = EnvCheckResult(mismatched={"ENV": ("prod", "staging")})
    summary = result.summary()
    assert "ENV" in summary
    assert "prod" in summary
    assert "staging" in summary


# ---------------------------------------------------------------------------
# env_check_from_config
# ---------------------------------------------------------------------------

def test_env_check_from_config_defaults():
    opts = env_check_from_config({})
    assert opts.required == []
    assert opts.expected == {}
    assert opts.warn_only is False


def test_env_check_from_config_full():
    raw = {"required": ["DB_URL"], "expected": {"ENV": "prod"}, "warn_only": True}
    opts = env_check_from_config(raw)
    assert opts.required == ["DB_URL"]
    assert opts.expected == {"ENV": "prod"}
    assert opts.warn_only is True
