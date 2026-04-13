"""Configuration loading for cronwatch."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import yaml

DEFAULT_CONFIG_PATH = os.path.expanduser("~/.cronwatch.yaml")


@dataclass
class SlackConfig:
    webhook_url: str = ""
    channel: str = ""
    notify_on_success: bool = False


@dataclass
class EmailConfig:
    smtp_host: str = "localhost"
    smtp_port: int = 25
    from_addr: str = ""
    to_addrs: List[str] = field(default_factory=list)
    notify_on_success: bool = False


@dataclass
class WebhookConfig:
    """Generic outbound webhook configuration."""
    url: str = ""
    method: str = "POST"
    headers: Dict[str, str] = field(
        default_factory=lambda: {"Content-Type": "application/json"}
    )
    notify_on_success: bool = False
    notify_on_failure: bool = True
    timeout: int = 10


@dataclass
class CronwatchConfig:
    log_dir: str = "/var/log/cronwatch"
    history_dir: str = "/var/lib/cronwatch"
    default_timeout: Optional[int] = None
    slack: Optional[SlackConfig] = None
    email: Optional[EmailConfig] = None
    webhook: Optional[WebhookConfig] = None


def load_config(path: str = DEFAULT_CONFIG_PATH) -> CronwatchConfig:
    """Load configuration from *path*, returning defaults if the file is absent."""
    if not os.path.exists(path):
        return CronwatchConfig()

    with open(path) as fh:
        raw = yaml.safe_load(fh) or {}

    slack = None
    if slack_raw := raw.get("slack"):
        slack = SlackConfig(**{k: v for k, v in slack_raw.items() if k in SlackConfig.__dataclass_fields__})

    email = None
    if email_raw := raw.get("email"):
        email = EmailConfig(**{k: v for k, v in email_raw.items() if k in EmailConfig.__dataclass_fields__})

    webhook = None
    if wh_raw := raw.get("webhook"):
        webhook = WebhookConfig(**{k: v for k, v in wh_raw.items() if k in WebhookConfig.__dataclass_fields__})

    return CronwatchConfig(
        log_dir=raw.get("log_dir", "/var/log/cronwatch"),
        history_dir=raw.get("history_dir", "/var/lib/cronwatch"),
        default_timeout=raw.get("default_timeout"),
        slack=slack,
        email=email,
        webhook=webhook,
    )
