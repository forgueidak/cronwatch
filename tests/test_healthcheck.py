"""Tests for cronwatch.healthcheck."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cronwatch.healthcheck import (
    HealthcheckOptions,
    PingResult,
    _send_ping,
    build_ping_url,
    send_healthcheck,
)
from cronwatch.runner import JobResult


def _make_result(returncode: int = 0) -> JobResult:
    return JobResult(
        command="echo hi",
        returncode=returncode,
        stdout="hi",
        stderr="",
        duration=0.1,
    )


# ---------------------------------------------------------------------------
# build_ping_url
# ---------------------------------------------------------------------------

def test_build_ping_url_appends_suffix():
    assert build_ping_url("https://hc.example.com/abc", "fail") == "https://hc.example.com/abc/fail"


def test_build_ping_url_strips_double_slash():
    assert build_ping_url("https://hc.example.com/abc/", "/fail") == "https://hc.example.com/abc/fail"


# ---------------------------------------------------------------------------
# PingResult
# ---------------------------------------------------------------------------

def test_ping_result_ok_on_2xx():
    pr = PingResult(url="http://x", status_code=200)
    assert pr.ok is True


def test_ping_result_not_ok_on_error():
    pr = PingResult(url="http://x", error="timeout")
    assert pr.ok is False


def test_ping_result_not_ok_on_5xx():
    pr = PingResult(url="http://x", status_code=500)
    assert pr.ok is False


# ---------------------------------------------------------------------------
# send_healthcheck — no URL configured
# ---------------------------------------------------------------------------

def test_send_healthcheck_no_url_returns_none():
    opts = HealthcheckOptions(ping_url="")
    assert send_healthcheck(_make_result(0), opts) is None


# ---------------------------------------------------------------------------
# send_healthcheck — success path
# ---------------------------------------------------------------------------

def test_send_healthcheck_success_pings_base_url():
    opts = HealthcheckOptions(ping_url="https://hc.example.com/token")
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: mock_resp
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        result = send_healthcheck(_make_result(0), opts)

    assert result is not None
    assert result.ok
    called_url = mock_open.call_args[0][0]
    assert called_url == "https://hc.example.com/token"


# ---------------------------------------------------------------------------
# send_healthcheck — failure path
# ---------------------------------------------------------------------------

def test_send_healthcheck_failure_pings_fail_suffix():
    opts = HealthcheckOptions(ping_url="https://hc.example.com/token", ping_on_failure=True)
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: mock_resp
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        result = send_healthcheck(_make_result(1), opts)

    assert result is not None
    called_url = mock_open.call_args[0][0]
    assert called_url.endswith("/fail")


def test_send_healthcheck_failure_suppressed_when_disabled():
    opts = HealthcheckOptions(ping_url="https://hc.example.com/token", ping_on_failure=False)
    result = send_healthcheck(_make_result(1), opts)
    assert result is None


# ---------------------------------------------------------------------------
# _send_ping — network error handling
# ---------------------------------------------------------------------------

def test_send_ping_captures_network_error():
    with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
        pr = _send_ping("https://hc.example.com/token", timeout=5)
    assert pr.ok is False
    assert "connection refused" in (pr.error or "")
