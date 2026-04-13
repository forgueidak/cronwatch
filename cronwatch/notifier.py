"""Slack and email notification support for cronwatch."""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

try:
    import requests
except ImportError:
    requests = None

from cronwatch.config import CronwatchConfig
from cronwatch.runner import JobResult

logger = logging.getLogger(__name__)


def _build_message(result: JobResult) -> str:
    status = "SUCCESS" if result.success else "FAILURE"
    lines = [
        f"*Cron Job {status}*",
        f"Command: `{result.command}`",
        f"Exit code: {result.exit_code}",
        f"Duration: {result.duration:.2f}s",
    ]
    if result.stderr:
        lines.append(f"Stderr:\n```{result.stderr[:500]}```")
    if result.stdout:
        lines.append(f"Stdout:\n```{result.stdout[:500]}```")
    return "\n".join(lines)


def notify_slack(result: JobResult, config: CronwatchConfig) -> bool:
    """Send a Slack notification via webhook. Returns True on success."""
    if not config.slack or not config.slack.webhook_url:
        return False
    if requests is None:
        logger.error("'requests' package is required for Slack notifications.")
        return False

    message = _build_message(result)
    payload = {"text": message}
    if config.slack.channel:
        payload["channel"] = config.slack.channel
    if config.slack.username:
        payload["username"] = config.slack.username

    try:
        resp = requests.post(config.slack.webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.debug("Slack notification sent successfully.")
        return True
    except Exception as exc:
        logger.error("Failed to send Slack notification: %s", exc)
        return False


def notify_email(result: JobResult, config: CronwatchConfig) -> bool:
    """Send an email notification. Returns True on success."""
    if not config.email or not config.email.to_addr:
        return False

    status = "SUCCESS" if result.success else "FAILURE"
    subject = f"[cronwatch] {status}: {result.command[:60]}"
    body = _build_message(result).replace("*", "").replace("`", "")

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = config.email.from_addr
    msg["To"] = config.email.to_addr
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(config.email.smtp_host, config.email.smtp_port, timeout=10) as server:
            if config.email.use_tls:
                server.starttls()
            if config.email.username and config.email.password:
                server.login(config.email.username, config.email.password)
            server.sendmail(config.email.from_addr, config.email.to_addr, msg.as_string())
        logger.debug("Email notification sent successfully.")
        return True
    except Exception as exc:
        logger.error("Failed to send email notification: %s", exc)
        return False


def send_notifications(result: JobResult, config: CronwatchConfig) -> None:
    """Dispatch all configured notifications based on job result and config."""
    should_notify = not result.success or config.notify_on_success
    if not should_notify:
        return
    notify_slack(result, config)
    notify_email(result, config)
