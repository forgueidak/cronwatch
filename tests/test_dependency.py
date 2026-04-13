"""Tests for cronwatch.dependency."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cronwatch.dependency import (
    DependencyOptions,
    DependencyResult,
    check_dependencies,
    _check_command,
    _check_tcp,
)


# ---------------------------------------------------------------------------
# DependencyOptions
# ---------------------------------------------------------------------------

class TestDependencyOptions:
    def test_defaults(self):
        opts = DependencyOptions()
        assert opts.commands == []
        assert opts.tcp_checks == []
        assert opts.enabled is True

    def test_from_dict_full(self):
        opts = DependencyOptions.from_dict(
            {"commands": ["curl"], "tcp_checks": ["localhost:5432"], "enabled": False}
        )
        assert opts.commands == ["curl"]
        assert opts.tcp_checks == ["localhost:5432"]
        assert opts.enabled is False

    def test_from_dict_empty(self):
        opts = DependencyOptions.from_dict({})
        assert opts.enabled is True


# ---------------------------------------------------------------------------
# DependencyResult
# ---------------------------------------------------------------------------

class TestDependencyResult:
    def test_ok_when_empty(self):
        assert DependencyResult().ok is True

    def test_not_ok_with_missing_command(self):
        r = DependencyResult(missing_commands=["psql"])
        assert r.ok is False

    def test_not_ok_with_failed_tcp(self):
        r = DependencyResult(failed_tcp=["localhost:5432"])
        assert r.ok is False

    def test_summary_ok(self):
        assert "satisfied" in DependencyResult().summary

    def test_summary_missing_commands(self):
        r = DependencyResult(missing_commands=["curl", "psql"])
        assert "curl" in r.summary
        assert "psql" in r.summary

    def test_summary_failed_tcp(self):
        r = DependencyResult(failed_tcp=["localhost:6379"])
        assert "localhost:6379" in r.summary


# ---------------------------------------------------------------------------
# check_dependencies
# ---------------------------------------------------------------------------

def test_check_dependencies_disabled_returns_none():
    opts = DependencyOptions(commands=["definitely_missing_xyz"], enabled=False)
    assert check_dependencies(opts) is None


def test_check_dependencies_all_present():
    # 'python' or 'python3' should always be on PATH in CI
    import sys, shutil
    py = "python3" if shutil.which("python3") else "python"
    opts = DependencyOptions(commands=[py])
    result = check_dependencies(opts)
    assert result is not None
    assert result.ok


def test_check_dependencies_missing_command():
    opts = DependencyOptions(commands=["__cronwatch_no_such_cmd__"])
    result = check_dependencies(opts)
    assert result is not None
    assert not result.ok
    assert "__cronwatch_no_such_cmd__" in result.missing_commands


def test_check_dependencies_failed_tcp():
    # Port 1 on localhost should be reliably closed
    opts = DependencyOptions(tcp_checks=["127.0.0.1:1"])
    result = check_dependencies(opts)
    assert result is not None
    assert not result.ok
    assert "127.0.0.1:1" in result.failed_tcp


def test_check_command_known_present():
    import shutil
    py = "python3" if shutil.which("python3") else "python"
    assert _check_command(py) is True


def test_check_command_missing():
    assert _check_command("__no_such_binary_xyz__") is False


def test_check_tcp_bad_address_format():
    # No colon — should return False gracefully
    assert _check_tcp("notavalidaddress") is False
