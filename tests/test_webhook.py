"""Tests for cronwatch.webhook."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock, patch
import urllib.error

import pytest

from cronwatch.runner import JobResult
from cronwatch.webhook import WebhookConfig, _build_payload, send_webhook


def _make_result(success: bool = True, stderr: str = "") -> JobResult:
    return JobResult(
        command="echo hi",
        exit_code=0 if success else 1,
        stdout="hi",
        stderr=stderr,
        duration=0.5,
        success=success,
        started_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


def _make_config(**kwargs) -> WebhookConfig:
    return WebhookConfig(url="https://example.com/hook", **kwargs)


# ---------------------------------------------------------------------------
# _build_payload
# ---------------------------------------------------------------------------

class TestBuildPayload:
    def test_contains_command(self):
        p = _build_payload(_make_result())
        assert p["command"] == "echo hi"

    def test_success_flag(self):
        assert _build_payload(_make_result(success=True))["success"] is True
        assert _build_payload(_make_result(success=False))["success"] is False

    def test_duration_rounded(self):
        r = _make_result()
        r = JobResult(**{**r.__dict__, "duration": 1.23456789})
        assert _build_payload(r)["duration"] == 1.235

    def test_started_at_iso(self):
        p = _build_payload(_make_result())
        assert "2024-01-15" in p["started_at"]


# ---------------------------------------------------------------------------
# send_webhook
# ---------------------------------------------------------------------------

class TestSendWebhook:
    def _mock_response(self, status: int = 200) -> MagicMock:
        resp = MagicMock()
        resp.status = status
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_success_skipped_by_default(self):
        cfg = _make_config(notify_on_success=False)
        result = send_webhook(_make_result(success=True), cfg)
        assert result is False

    def test_failure_sent_by_default(self):
        cfg = _make_config()
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value = self._mock_response(200)
            result = send_webhook(_make_result(success=False), cfg)
        assert result is True

    def test_success_sent_when_flag_set(self):
        cfg = _make_config(notify_on_success=True)
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value = self._mock_response(200)
            result = send_webhook(_make_result(success=True), cfg)
        assert result is True

    def test_http_error_returns_false(self):
        cfg = _make_config()
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            url="", code=500, msg="Server Error", hdrs=None, fp=None
        )):
            result = send_webhook(_make_result(success=False), cfg)
        assert result is False

    def test_url_error_returns_false(self):
        cfg = _make_config()
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            result = send_webhook(_make_result(success=False), cfg)
        assert result is False

    def test_payload_is_valid_json(self):
        cfg = _make_config(notify_on_failure=True)
        captured = {}

        def fake_open(req, timeout):
            captured["body"] = json.loads(req.data.decode())
            resp = self._mock_response()
            return resp

        with patch("urllib.request.urlopen", side_effect=fake_open):
            send_webhook(_make_result(success=False), cfg)

        assert "command" in captured["body"]
        assert "exit_code" in captured["body"]

    def test_failure_skipped_when_flag_false(self):
        cfg = _make_config(notify_on_failure=False)
        result = send_webhook(_make_result(success=False), cfg)
        assert result is False
