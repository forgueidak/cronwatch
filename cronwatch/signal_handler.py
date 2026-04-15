"""Signal handler for graceful shutdown of cronwatch processes."""

from __future__ import annotations

import signal
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class SignalOptions:
    enabled: bool = True
    notify_on_interrupt: bool = True
    signals: list[str] = field(default_factory=lambda: ["SIGTERM", "SIGINT"])

    @classmethod
    def from_dict(cls, data: dict) -> "SignalOptions":
        return cls(
            enabled=bool(data.get("enabled", True)),
            notify_on_interrupt=bool(data.get("notify_on_interrupt", True)),
            signals=list(data.get("signals", ["SIGTERM", "SIGINT"])),
        )


@dataclass
class SignalResult:
    received: Optional[str] = None
    interrupted: bool = False

    def ok(self) -> bool:
        return not self.interrupted

    def summary(self) -> str:
        if not self.interrupted:
            return "no signal received"
        return f"interrupted by {self.received}"


class SignalHandler:
    """Registers OS signal handlers and tracks whether a shutdown was requested."""

    def __init__(self, opts: SignalOptions) -> None:
        self.opts = opts
        self._result = SignalResult()
        self._original: dict[int, object] = {}
        self._callbacks: list[Callable[[str], None]] = []

    def add_callback(self, cb: Callable[[str], None]) -> None:
        self._callbacks.append(cb)

    def install(self) -> None:
        if not self.opts.enabled:
            return
        for sig_name in self.opts.signals:
            sig_num = getattr(signal, sig_name, None)
            if sig_num is None:
                logger.warning("Unknown signal: %s — skipping", sig_name)
                continue
            self._original[sig_num] = signal.getsignal(sig_num)
            signal.signal(sig_num, self._handle)
            logger.debug("Installed handler for %s", sig_name)

    def restore(self) -> None:
        for sig_num, original in self._original.items():
            signal.signal(sig_num, original)
        self._original.clear()

    def _handle(self, signum: int, frame: object) -> None:
        sig_name = signal.Signals(signum).name
        logger.warning("Received signal %s — requesting shutdown", sig_name)
        self._result = SignalResult(received=sig_name, interrupted=True)
        for cb in self._callbacks:
            try:
                cb(sig_name)
            except Exception:
                logger.exception("Error in signal callback")

    def result(self) -> SignalResult:
        return self._result

    def interrupted(self) -> bool:
        return self._result.interrupted
