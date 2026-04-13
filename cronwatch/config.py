"""Configuration loading for cronwatch."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class SlackConfig:
    webhook_url: str = ""
    channel: str = ""
    username: str = "cronwatch"


@dataclass
class EmailConfig:
    smtp_host: str = "localhost"
    smtp_port: int = 25
    from_address: str = ""
    to_addresses: list[str] = field(default_factory=list)
    use_tls: bool = False
    username: str = ""
    password: str = ""


@dataclass
class WebhookConfig:
    url: str = ""
    secret: str = ""
    timeout_seconds: int = 10


@dataclass
class ThrottleConfig:
    cooldown_seconds: int = 3600
    state_dir: str = "/tmp/cronwatch/throttle"


@dataclass
class CronwatchConfig:
    log_dir: str = "/tmp/cronwatch/logs"
    history_dir: str = "/tmp/cronwatch/history"
    default_timeout: Optional[int] = None
    notify_on_success: bool = False
    slack: SlackConfig = field(default_factory=SlackConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    webhook: WebhookConfig = field(default_factory=WebhookConfig)
    throttle: ThrottleConfig = field(default_factory=ThrottleConfig)


def load_config(path: Optional[str] = None) -> CronwatchConfig:
    """Load configuration from a YAML file, falling back to defaults."""
    if path is None:
        default_locations = [
            Path.home() / ".config" / "cronwatch" / "config.yaml",
            Path("/etc/cronwatch/config.yaml"),
        ]
        for loc in default_locations:
            if loc.exists():
                path = str(loc)
                break

    if path is None or not Path(path).exists():
        return CronwatchConfig()

    with open(path) as fh:
        raw = yaml.safe_load(fh) or {}

    slack_raw = raw.get("slack", {})
    email_raw = raw.get("email", {})
    webhook_raw = raw.get("webhook", {})
    throttle_raw = raw.get("throttle", {})

    return CronwatchConfig(
        log_dir=raw.get("log_dir", "/tmp/cronwatch/logs"),
        history_dir=raw.get("history_dir", "/tmp/cronwatch/history"),
        default_timeout=raw.get("default_timeout"),
        notify_on_success=raw.get("notify_on_success", False),
        slack=SlackConfig(
            webhook_url=slack_raw.get("webhook_url", ""),
            channel=slack_raw.get("channel", ""),
            username=slack_raw.get("username", "cronwatch"),
        ),
        email=EmailConfig(
            smtp_host=email_raw.get("smtp_host", "localhost"),
            smtp_port=email_raw.get("smtp_port", 25),
            from_address=email_raw.get("from_address", ""),
            to_addresses=email_raw.get("to_addresses", []),
            use_tls=email_raw.get("use_tls", False),
            username=email_raw.get("username", ""),
            password=email_raw.get("password", ""),
        ),
        webhook=WebhookConfig(
            url=webhook_raw.get("url", ""),
            secret=webhook_raw.get("secret", ""),
            timeout_seconds=webhook_raw.get("timeout_seconds", 10),
        ),
        throttle=ThrottleConfig(
            cooldown_seconds=throttle_raw.get("cooldown_seconds", 3600),
            state_dir=throttle_raw.get("state_dir", "/tmp/cronwatch/throttle"),
        ),
    )
