"""Dependency checking: verify required commands/services are available before running a job."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DependencyOptions:
    commands: List[str] = field(default_factory=list)  # e.g. ["curl", "psql"]
    tcp_checks: List[str] = field(default_factory=list)  # e.g. ["localhost:5432"]
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "DependencyOptions":
        return cls(
            commands=data.get("commands", []),
            tcp_checks=data.get("tcp_checks", []),
            enabled=data.get("enabled", True),
        )


@dataclass
class DependencyResult:
    missing_commands: List[str] = field(default_factory=list)
    failed_tcp: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing_commands and not self.failed_tcp

    @property
    def summary(self) -> str:
        if self.ok:
            return "All dependencies satisfied."
        parts = []
        if self.missing_commands:
            parts.append("Missing commands: " + ", ".join(self.missing_commands))
        if self.failed_tcp:
            parts.append("Unreachable hosts: " + ", ".join(self.failed_tcp))
        return "; ".join(parts)


def _check_command(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _check_tcp(host_port: str, timeout: int = 3) -> bool:
    """Use nc (netcat) or a raw socket to verify TCP connectivity."""
    try:
        host, port_str = host_port.rsplit(":", 1)
        port = int(port_str)
    except ValueError:
        return False
    try:
        result = subprocess.run(
            ["nc", "-z", "-w", str(timeout), host, str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout + 1,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        # fallback: try Python socket
        import socket
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False


def check_dependencies(opts: DependencyOptions) -> Optional[DependencyResult]:
    """Return None if checking is disabled, otherwise a DependencyResult."""
    if not opts.enabled:
        return None

    result = DependencyResult()

    for cmd in opts.commands:
        if not _check_command(cmd):
            result.missing_commands.append(cmd)

    for addr in opts.tcp_checks:
        if not _check_tcp(addr):
            result.failed_tcp.append(addr)

    return result
