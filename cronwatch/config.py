"""Configuration loader for cronwatch."""

import os
import yaml
from dataclasses import dataclass, field
from typing import Optional


DEFAULT_CONFIG_PATH = os.path.expanduser("~/.cronwatch/config.yaml")


@dataclass
class SlackConfig:
    webhook_url: Optional[str] = None
    channel: Optional[str] = None


@dataclass
class EmailConfig:
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    username: Optional[str] = None
    password: Optional[str] = None
    from_addr: Optional[str] = None
    to_addrs: list = field(default_factory=list)


@dataclass
class CronwatchConfig:
    log_dir: str = "/var/log/cronwatch"
    retention_days: int = 30
    slack: SlackConfig = field(default_factory=SlackConfig)
    email: EmailConfig = field(default_factory=EmailConfig)


def load_config(path: str = DEFAULT_CONFIG_PATH) -> CronwatchConfig:
    """Load configuration from a YAML file.

    Falls back to defaults if the file does not exist.
    """
    if not os.path.exists(path):
        return CronwatchConfig()

    with open(path, "r") as fh:
        raw = yaml.safe_load(fh) or {}

    slack_raw = raw.get("slack", {})
    email_raw = raw.get("email", {})

    return CronwatchConfig(
        log_dir=raw.get("log_dir", "/var/log/cronwatch"),
        retention_days=int(raw.get("retention_days", 30)),
        slack=SlackConfig(
            webhook_url=slack_raw.get("webhook_url"),
            channel=slack_raw.get("channel"),
        ),
        email=EmailConfig(
            smtp_host=email_raw.get("smtp_host"),
            smtp_port=int(email_raw.get("smtp_port", 587)),
            username=email_raw.get("username"),
            password=email_raw.get("password"),
            from_addr=email_raw.get("from_addr"),
            to_addrs=email_raw.get("to_addrs", []),
        ),
    )
