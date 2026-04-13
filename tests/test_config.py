"""Tests for cronwatch.config module."""

import os
import textwrap
import pytest

from cronwatch.config import load_config, CronwatchConfig, SlackConfig, EmailConfig


def test_load_config_defaults_when_file_missing(tmp_path):
    """Returns a default config when the file does not exist."""
    cfg = load_config(path=str(tmp_path / "nonexistent.yaml"))
    assert isinstance(cfg, CronwatchConfig)
    assert cfg.log_dir == "/var/log/cronwatch"
    assert cfg.retention_days == 30
    assert cfg.slack.webhook_url is None
    assert cfg.email.to_addrs == []


def test_load_config_empty_file(tmp_path):
    """Returns defaults when the YAML file is empty."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("")
    cfg = load_config(path=str(config_file))
    assert cfg.retention_days == 30


def test_load_config_full(tmp_path):
    """Parses all supported fields correctly."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        textwrap.dedent("""
            log_dir: /tmp/cw_logs
            retention_days: 7
            slack:
              webhook_url: https://hooks.slack.com/test
              channel: "#ops"
            email:
              smtp_host: mail.example.com
              smtp_port: 465
              username: user@example.com
              password: secret
              from_addr: user@example.com
              to_addrs:
                - a@example.com
                - b@example.com
        """)
    )
    cfg = load_config(path=str(config_file))

    assert cfg.log_dir == "/tmp/cw_logs"
    assert cfg.retention_days == 7
    assert cfg.slack.webhook_url == "https://hooks.slack.com/test"
    assert cfg.slack.channel == "#ops"
    assert cfg.email.smtp_host == "mail.example.com"
    assert cfg.email.smtp_port == 465
    assert cfg.email.to_addrs == ["a@example.com", "b@example.com"]


def test_load_config_partial_slack(tmp_path):
    """Handles partial slack config without raising."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("slack:\n  webhook_url: https://hooks.slack.com/x\n")
    cfg = load_config(path=str(config_file))
    assert cfg.slack.webhook_url == "https://hooks.slack.com/x"
    assert cfg.slack.channel is None
