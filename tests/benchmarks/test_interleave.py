"""
CodSpeed benchmarks for ``_interleave_addrinfos``.

This is the hot path PR #239 rewrites (dict ``try/except KeyError`` ->
``defaultdict``); the benchmark exists so that change can be measured against
the baseline on ``main``.
"""

from __future__ import annotations

import pytest

from aiohappyeyeballs.impl import _interleave_addrinfos

from ._data import SCENARIO_IDS, SCENARIOS, make_addrinfos

try:
    from pytest_codspeed import BenchmarkFixture
except ImportError:  # pragma: no cover - only when pytest-codspeed is absent
    pytestmark = pytest.mark.skip("pytest-codspeed not installed")


@pytest.mark.parametrize("first_address_family_count", (1, 2))
@pytest.mark.parametrize(("n_v6", "n_v4"), SCENARIOS, ids=SCENARIO_IDS)
def test_interleave_addrinfos(
    benchmark: BenchmarkFixture,
    n_v6: int,
    n_v4: int,
    first_address_family_count: int,
) -> None:
    sample = make_addrinfos(n_v6, n_v4)

    # Interleaving is a pure reordering, so nothing is dropped. Asserting once
    # outside the measured loop keeps a no-op refactor from reporting a fake
    # speedup against a function that stopped doing its job.
    assert len(_interleave_addrinfos(sample, first_address_family_count)) == len(sample)

    @benchmark
    def run() -> None:
        _interleave_addrinfos(sample, first_address_family_count)
