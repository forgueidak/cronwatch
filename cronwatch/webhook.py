"""Generic webhook notification support for cronwatch."""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from cronwatch.runner import JobResult

log = logging.getLogger(__name__)


@dataclass
class WebhookConfig:
    url: str
    method: str = "POST"
    headers: Dict[str, str] = field(default_factory=lambda: {"Content-Type": "application/json"})
    notify_on_success: bool = False
    notify_on_failure: bool = True
    timeout: int = 10


def _build_payload(result: JobResult) -> Dict[str, Any]:
    """Build a JSON-serialisable payload from a JobResult."""
    return {
        "command": result.command,
        "exit_code": result.exit_code,
        "success": result.success,
        "duration": round(result.duration, 3),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "started_at": result.started_at.isoformat() if result.started_at else None,
    }


def send_webhook(
    result: JobResult,
    config: WebhookConfig,
) -> bool:
    """POST *result* to the configured webhook URL.

    Returns True on success, False on any network/HTTP error.
    """
    if result.success and not config.notify_on_success:
        log.debug("Webhook skipped (success, notify_on_success=False)")
        return False
    if not result.success and not config.notify_on_failure:
        log.debug("Webhook skipped (failure, notify_on_failure=False)")
        return False

    payload = json.dumps(_build_payload(result)).encode()
    req = urllib.request.Request(
        url=config.url,
        data=payload,
        method=config.method.upper(),
        headers=config.headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=config.timeout) as resp:
            status = resp.status
            log.info("Webhook delivered, HTTP %s", status)
            return True
    except urllib.error.HTTPError as exc:
        log.error("Webhook HTTP error %s: %s", exc.code, exc.reason)
    except urllib.error.URLError as exc:
        log.error("Webhook URL error: %s", exc.reason)
    except Exception as exc:  # pragma: no cover
        log.error("Webhook unexpected error: %s", exc)
    return False
