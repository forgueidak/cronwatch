"""Integration tests for the circuit breaker across multiple job runs."""
from pathlib import Path

import pytest

from cronwatch.circuit_breaker import CircuitBreakerOptions, check_circuit, load_circuit_state


@pytest.fixture()
def state_dir(tmp_path: Path) -> str:
    return str(tmp_path / "circuit")


def _opts(state_dir: str) -> CircuitBreakerOptions:
    return CircuitBreakerOptions(
        enabled=True,
        failure_threshold=3,
        cooldown_seconds=60,
        state_dir=state_dir,
    )


def test_full_open_cooldown_close_cycle(state_dir):
    """Simulate a job failing until the circuit opens, then recovering."""
    opts = _opts(state_dir)
    base = 1_000_000.0

    # Three consecutive failures open the circuit.
    for i in range(3):
        r = check_circuit("job", opts, succeeded=False, now=base + i)
        assert r.allowed, f"run {i} should be allowed before threshold"

    state = load_circuit_state("job", opts.state_dir)
    assert state.status == "open"

    # During cooldown subsequent attempts are blocked.
    blocked = check_circuit("job", opts, succeeded=False, now=base + 10)
    assert not blocked.allowed

    # After cooldown a probe is allowed and succeeds -> circuit closes.
    probe = check_circuit("job", opts, succeeded=True, now=base + 120)
    assert probe.allowed
    state = load_circuit_state("job", opts.state_dir)
    assert state.status == "closed"
    assert state.consecutive_failures == 0


def test_half_open_probe_failure_reopens(state_dir):
    """A failed probe in half-open state should reopen the circuit."""
    opts = _opts(state_dir)
    base = 2_000_000.0

    for i in range(3):
        check_circuit("job", opts, succeeded=False, now=base + i)

    # Probe after cooldown — but it fails.
    check_circuit("job", opts, succeeded=False, now=base + 120)

    state = load_circuit_state("job", opts.state_dir)
    assert state.status == "open"
    # opened_at should have been refreshed
    assert state.opened_at is not None and state.opened_at >= base + 120


def test_intermittent_failures_do_not_open(state_dir):
    """Failures separated by successes should never reach the threshold."""
    opts = _opts(state_dir)
    base = 3_000_000.0
    for i in range(10):
        check_circuit("job", opts, succeeded=(i % 2 == 0), now=base + i)

    state = load_circuit_state("job", opts.state_dir)
    assert state.status != "open"
