"""Healthcheck ping support — send HTTP pings to uptime monitoring services."""

from __future__ import annotations

import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional

from cronwatch.runner import JobResult


@dataclass
class HealthcheckOptions:
    """Configuration for healthcheck ping behaviour."""

    ping_url: str = ""
    ping_on_start: bool = False
    ping_on_failure: bool = True
    timeout_seconds: int = 10


@dataclass
class PingResult:
    url: str
    status_code: Optional[int] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.status_code is not None and 200 <= self.status_code < 300


def _send_ping(url: str, timeout: int) -> PingResult:
    """Send a single HTTP GET ping and return the result."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return PingResult(url=url, status_code=resp.status)
    except urllib.error.HTTPError as exc:
        return PingResult(url=url, status_code=exc.code, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return PingResult(url=url, error=str(exc))


def build_ping_url(base_url: str, suffix: str) -> str:
    """Append a path suffix to a base URL, handling trailing slashes."""
    return base_url.rstrip("/") + "/" + suffix.lstrip("/")


def send_healthcheck(
    result: JobResult,
    opts: HealthcheckOptions,
) -> Optional[PingResult]:
    """Ping the healthcheck URL based on job outcome.

    Returns the PingResult if a ping was sent, otherwise None.
    """
    if not opts.ping_url:
        return None

    if result.returncode == 0:
        return _send_ping(opts.ping_url, opts.timeout_seconds)

    # Job failed
    if opts.ping_on_failure:
        failure_url = build_ping_url(opts.ping_url, "fail")
        return _send_ping(failure_url, opts.timeout_seconds)

    return None
