"""Tests for cronwatch.notifier module."""

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

from cronwatch.notifier import notify_slack, notify_email, send_notifications, _build_message
from cronwatch.config import CronwatchConfig, SlackConfig, EmailConfig
from cronwatch.runner import JobResult


def _make_result(success=True, exit_code=0, stderr="", stdout=""):
    return JobResult(
        command="echo hello",
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration=1.23,
        success=success,
    )


def _make_config(slack=None, email=None, notify_on_success=False):
    return CronwatchConfig(slack=slack, email=email, notify_on_success=notify_on_success)


class TestBuildMessage:
    def test_success_message_contains_command(self):
        result = _make_result(success=True)
        msg = _build_message(result)
        assert "echo hello" in msg
        assert "SUCCESS" in msg

    def test_failure_message_contains_stderr(self):
        result = _make_result(success=False, exit_code=1, stderr="something went wrong")
        msg = _build_message(result)
        assert "FAILURE" in msg
        assert "something went wrong" in msg


class TestNotifySlack:
    def test_returns_false_when_no_slack_config(self):
        result = _make_result()
        config = _make_config()
        assert notify_slack(result, config) is False

    def test_returns_false_when_no_webhook_url(self):
        result = _make_result()
        config = _make_config(slack=SlackConfig(webhook_url=""))
        assert notify_slack(result, config) is False

    @patch("cronwatch.notifier.requests")
    def test_sends_post_request(self, mock_requests):
        mock_resp = MagicMock()
        mock_requests.post.return_value = mock_resp
        result = _make_result()
        config = _make_config(slack=SlackConfig(webhook_url="https://hooks.slack.com/test"))
        assert notify_slack(result, config) is True
        mock_requests.post.assert_called_once()

    @patch("cronwatch.notifier.requests")
    def test_returns_false_on_request_error(self, mock_requests):
        mock_requests.post.side_effect = Exception("connection error")
        result = _make_result()
        config = _make_config(slack=SlackConfig(webhook_url="https://hooks.slack.com/test"))
        assert notify_slack(result, config) is False


class TestNotifyEmail:
    def test_returns_false_when_no_email_config(self):
        result = _make_result()
        config = _make_config()
        assert notify_email(result, config) is False

    @patch("cronwatch.notifier.smtplib.SMTP")
    def test_sends_email(self, mock_smtp_cls):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__ = lambda s: mock_smtp
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        result = _make_result(success=False, exit_code=1)
        email_cfg = EmailConfig(
            smtp_host="localhost", smtp_port=25,
            from_addr="cron@example.com", to_addr="ops@example.com"
        )
        config = _make_config(email=email_cfg)
        assert notify_email(result, config) is True


class TestSendNotifications:
    @patch("cronwatch.notifier.notify_slack", return_value=True)
    @patch("cronwatch.notifier.notify_email", return_value=True)
    def test_notifies_on_failure(self, mock_email, mock_slack):
        result = _make_result(success=False)
        config = _make_config()
        send_notifications(result, config)
        mock_slack.assert_called_once()
        mock_email.assert_called_once()

    @patch("cronwatch.notifier.notify_slack", return_value=True)
    @patch("cronwatch.notifier.notify_email", return_value=True)
    def test_skips_on_success_without_flag(self, mock_email, mock_slack):
        result = _make_result(success=True)
        config = _make_config(notify_on_success=False)
        send_notifications(result, config)
        mock_slack.assert_not_called()
        mock_email.assert_not_called()
