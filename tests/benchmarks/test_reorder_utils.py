"""
CodSpeed benchmarks for the in-place addrinfo reducers in ``utils``.

``pop_addr_infos_interleave`` and ``remove_addr_infos`` both mutate their input
list (``addr_infos[:] = kept``), so each measured call operates on a fresh
``sample.copy()``. The copy cost is identical for the base and the PR, so the
relative comparison CodSpeed reports stays valid.
"""

from __future__ import annotations

import ipaddress

import pytest

from aiohappyeyeballs.utils import pop_addr_infos_interleave, remove_addr_infos

from ._data import SCENARIO_IDS, SCENARIOS, make_addrinfos

try:
    from pytest_codspeed import BenchmarkFixture
except ImportError:  # pragma: no cover - only when pytest-codspeed is absent
    pytestmark = pytest.mark.skip("pytest-codspeed not installed")


@pytest.mark.parametrize(("n_v6", "n_v4"), SCENARIOS, ids=SCENARIO_IDS)
def test_pop_addr_infos_interleave(
    benchmark: BenchmarkFixture, n_v6: int, n_v4: int
) -> None:
    sample = make_addrinfos(n_v6, n_v4)
    # interleave=1 drops the first entry of each family present.
    families = (n_v6 > 0) + (n_v4 > 0)

    probe = sample.copy()
    pop_addr_infos_interleave(probe, 1)
    assert len(probe) == len(sample) - families

    @benchmark
    def run() -> None:
        pop_addr_infos_interleave(sample.copy(), 1)


def test_remove_addr_infos_fast_path(benchmark: BenchmarkFixture) -> None:
    sample = make_addrinfos(4, 4)
    # Exact sockaddr of an entry -> the ``ai[-1] != addr`` fast path removes it.
    target = sample[-1][-1]

    probe = sample.copy()
    remove_addr_infos(probe, target)
    assert len(probe) == len(sample) - 1

    @benchmark
    def run() -> None:
        remove_addr_infos(sample.copy(), target)


def test_remove_addr_infos_slow_path(benchmark: BenchmarkFixture) -> None:
    sample = make_addrinfos(4, 4)
    # sample[0] is a v6 entry; target the same IP in fully-expanded form so the
    # tuple compare misses and the ipaddress() normalization slow path runs.
    v6_host = sample[0][-1][0]
    target = (ipaddress.ip_address(v6_host).exploded, 80, 0, 0)

    probe = sample.copy()
    remove_addr_infos(probe, target)
    assert len(probe) == len(sample) - 1

    @benchmark
    def run() -> None:
        remove_addr_infos(sample.copy(), target)
