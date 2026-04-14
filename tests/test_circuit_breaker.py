"""Tests for cronwatch.circuit_breaker."""
import json
import time
from pathlib import Path

import pytest

from cronwatch.circuit_breaker import (
    CircuitBreakerOptions,
    CircuitResult,
    CircuitState,
    _state_path,
    check_circuit,
    load_circuit_state,
    save_circuit_state,
)


@pytest.fixture()
def state_dir(tmp_path: Path) -> str:
    return str(tmp_path / "circuit")


def _opts(state_dir: str, threshold: int = 3, cooldown: int = 300) -> CircuitBreakerOptions:
    return CircuitBreakerOptions(
        enabled=True,
        failure_threshold=threshold,
        cooldown_seconds=cooldown,
        state_dir=state_dir,
    )


# ---------------------------------------------------------------------------
# CircuitBreakerOptions.from_dict
# ---------------------------------------------------------------------------

class TestCircuitBreakerOptionsFromDict:
    def test_defaults(self):
        opts = CircuitBreakerOptions.from_dict({})
        assert opts.enabled is False
        assert opts.failure_threshold == 3
        assert opts.cooldown_seconds == 300

    def test_full(self):
        opts = CircuitBreakerOptions.from_dict(
            {"enabled": True, "failure_threshold": 5, "cooldown_seconds": 60,
             "state_dir": "/tmp/x"}
        )
        assert opts.enabled is True
        assert opts.failure_threshold == 5
        assert opts.cooldown_seconds == 60
        assert opts.state_dir == "/tmp/x"


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def test_load_missing_returns_closed(state_dir):
    state = load_circuit_state("myjob", state_dir)
    assert state.status == "closed"
    assert state.consecutive_failures == 0
    assert state.opened_at is None


def test_save_and_load_roundtrip(state_dir):
    original = CircuitState(status="open", consecutive_failures=4, opened_at=12345.0)
    save_circuit_state("myjob", original, state_dir)
    loaded = load_circuit_state("myjob", state_dir)
    assert loaded.status == "open"
    assert loaded.consecutive_failures == 4
    assert loaded.opened_at == 12345.0


def test_state_path_sanitizes_slashes(state_dir):
    path = _state_path("a/b/c", state_dir)
    assert "/" not in path.name


# ---------------------------------------------------------------------------
# check_circuit logic
# ---------------------------------------------------------------------------

def test_disabled_always_allows(state_dir):
    opts = CircuitBreakerOptions(enabled=False, state_dir=state_dir)
    result = check_circuit("job", opts, succeeded=False)
    assert result.allowed is True
    assert result.status == "disabled"


def test_single_failure_does_not_open(state_dir):
    opts = _opts(state_dir, threshold=3)
    result = check_circuit("job", opts, succeeded=False)
    assert result.allowed is True
    assert result.status == "closed"


def test_circuit_opens_after_threshold(state_dir):
    opts = _opts(state_dir, threshold=2)
    check_circuit("job", opts, succeeded=False)
    result = check_circuit("job", opts, succeeded=False)
    assert result.allowed is True   # the run that triggered opening is still allowed
    state = load_circuit_state("job", opts.state_dir)
    assert state.status == "open"


def test_open_circuit_blocks_run(state_dir):
    opts = _opts(state_dir, threshold=1, cooldown=9999)
    now = time.time()
    check_circuit("job", opts, succeeded=False, now=now)
    result = check_circuit("job", opts, succeeded=False, now=now + 1)
    assert result.allowed is False
    assert "cooldown" in result.reason


def test_circuit_allows_after_cooldown(state_dir):
    opts = _opts(state_dir, threshold=1, cooldown=10)
    now = time.time()
    check_circuit("job", opts, succeeded=False, now=now)
    result = check_circuit("job", opts, succeeded=True, now=now + 20)
    assert result.allowed is True


def test_success_closes_circuit(state_dir):
    opts = _opts(state_dir, threshold=1, cooldown=1)
    now = time.time()
    check_circuit("job", opts, succeeded=False, now=now)
    check_circuit("job", opts, succeeded=True, now=now + 5)
    state = load_circuit_state("job", opts.state_dir)
    assert state.status == "closed"
    assert state.consecutive_failures == 0


def test_circuit_result_summary_allowed(state_dir):
    opts = _opts(state_dir)
    result = check_circuit("job", opts, succeeded=True)
    assert "allowed" in result.summary()


def test_circuit_result_summary_blocked(state_dir):
    opts = _opts(state_dir, threshold=1, cooldown=9999)
    now = time.time()
    check_circuit("job", opts, succeeded=False, now=now)
    result = check_circuit("job", opts, succeeded=False, now=now + 1)
    assert "open" in result.summary()
