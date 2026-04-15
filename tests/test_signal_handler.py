"""Tests for cronwatch.signal_handler."""

from __future__ import annotations

import signal
import pytest

from cronwatch.signal_handler import (
    SignalOptions,
    SignalResult,
    SignalHandler,
)


# ---------------------------------------------------------------------------
# SignalOptions.from_dict
# ---------------------------------------------------------------------------

class TestSignalOptionsFromDict:
    def test_defaults(self):
        opts = SignalOptions()
        assert opts.enabled is True
        assert opts.notify_on_interrupt is True
        assert "SIGTERM" in opts.signals
        assert "SIGINT" in opts.signals

    def test_from_dict_full(self):
        opts = SignalOptions.from_dict({
            "enabled": False,
            "notify_on_interrupt": False,
            "signals": ["SIGTERM"],
        })
        assert opts.enabled is False
        assert opts.notify_on_interrupt is False
        assert opts.signals == ["SIGTERM"]

    def test_from_dict_empty_uses_defaults(self):
        opts = SignalOptions.from_dict({})
        assert opts.enabled is True


# ---------------------------------------------------------------------------
# SignalResult
# ---------------------------------------------------------------------------

class TestSignalResult:
    def test_ok_when_not_interrupted(self):
        r = SignalResult()
        assert r.ok() is True

    def test_not_ok_when_interrupted(self):
        r = SignalResult(received="SIGTERM", interrupted=True)
        assert r.ok() is False

    def test_summary_no_signal(self):
        assert "no signal" in SignalResult().summary()

    def test_summary_with_signal(self):
        r = SignalResult(received="SIGINT", interrupted=True)
        assert "SIGINT" in r.summary()


# ---------------------------------------------------------------------------
# SignalHandler behaviour
# ---------------------------------------------------------------------------

class TestSignalHandler:
    def test_install_and_restore_does_not_raise(self):
        opts = SignalOptions(signals=["SIGTERM"])
        handler = SignalHandler(opts)
        handler.install()
        assert not handler.interrupted()
        handler.restore()

    def test_disabled_install_skips_registration(self):
        opts = SignalOptions(enabled=False, signals=["SIGTERM"])
        handler = SignalHandler(opts)
        handler.install()
        assert handler._original == {}

    def test_handle_sets_interrupted(self):
        opts = SignalOptions(signals=["SIGUSR1"])
        handler = SignalHandler(opts)
        handler.install()
        signal.raise_signal(signal.SIGUSR1)
        assert handler.interrupted() is True
        assert handler.result().received == "SIGUSR1"
        handler.restore()

    def test_callback_invoked_on_signal(self):
        received: list[str] = []
        opts = SignalOptions(signals=["SIGUSR2"])
        handler = SignalHandler(opts)
        handler.add_callback(received.append)
        handler.install()
        signal.raise_signal(signal.SIGUSR2)
        assert received == ["SIGUSR2"]
        handler.restore()

    def test_unknown_signal_name_skipped(self):
        opts = SignalOptions(signals=["SIGNOTREAL"])
        handler = SignalHandler(opts)
        handler.install()  # should not raise
        assert handler._original == {}
