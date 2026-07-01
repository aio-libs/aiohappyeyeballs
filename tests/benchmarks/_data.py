"""
Sample addrinfo data for the CodSpeed benchmark suite.

Reuses the addrinfo tuple shapes exercised in ``tests/test_utils.py`` and
``tests/test_impl.py`` so the benchmarks measure the same objects the
production hot paths handle.
"""

from __future__ import annotations

import socket

from aiohappyeyeballs.types import AddrInfoType


def _v6(host: str, port: int = 80) -> AddrInfoType:
    return (
        socket.AF_INET6,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        (host, port, 0, 0),
    )


def _v4(host: str, port: int = 80) -> AddrInfoType:
    return (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (host, port))


def make_addrinfos(n_v6: int, n_v4: int) -> list[AddrInfoType]:
    """
    Build an addrinfo list of ``n_v6`` IPv6 entries followed by ``n_v4`` IPv4 entries.

    Each entry gets a distinct address so ``remove_addr_infos`` benchmarks can
    target a single one.
    """
    infos: list[AddrInfoType] = [_v6(f"dead:beef::{i:x}") for i in range(n_v6)]
    infos += [_v4(f"107.6.106.{i}") for i in range(n_v4)]
    return infos


# (n_v6, n_v4) per scenario, with matching human-readable ids.
SCENARIOS = [(1, 1), (4, 4), (16, 16), (0, 8)]
SCENARIO_IDS = ["small_mixed", "mixed", "large_mixed", "single_family"]
