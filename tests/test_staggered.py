import asyncio
import sys
from functools import partial

import pytest

from aiohappyeyeballs._staggered import staggered_race


@pytest.mark.asyncio
async def test_one_winners():
    """Test that there is only one winner when there is no await in the coro."""
    winners = []

    async def coro(idx):
        winners.append(idx)
        return idx

    coros = [partial(coro, idx) for idx in range(4)]

    winner, index, excs = await staggered_race(
        coros,
        delay=None,
    )
    assert len(winners) == 1
    assert winners == [0]
    assert winner == 0
    assert index == 0
    assert excs == [None]


@pytest.mark.asyncio
async def test_multiple_winners():
    """Test multiple winners are handled correctly."""
    loop = asyncio.get_running_loop()
    winners = []
    finish = loop.create_future()

    async def coro(idx):
        await finish
        winners.append(idx)
        return idx

    coros = [partial(coro, idx) for idx in range(4)]

    task = loop.create_task(staggered_race(coros, delay=0.00001))
    await asyncio.sleep(0.1)
    loop.call_soon(finish.set_result, None)
    winner, index, excs = await task
    assert len(winners) == 4
    assert winners == [0, 1, 2, 3]
    assert winner == 0
    assert index == 0
    assert excs == [None, None, None, None]


@pytest.mark.skipif(sys.version_info < (3, 12), reason="requires python3.12 or higher")
def test_multiple_winners_eager_task_factory():
    """Test multiple winners are handled correctly."""
    loop = asyncio.new_event_loop()
    eager_task_factory = asyncio.create_eager_task_factory(asyncio.Task)
    loop.set_task_factory(eager_task_factory)
    asyncio.set_event_loop(None)

    async def run():
        winners = []
        finish = loop.create_future()

        async def coro(idx):
            await finish
            winners.append(idx)
            return idx

        coros = [partial(coro, idx) for idx in range(4)]

        task = loop.create_task(staggered_race(coros, delay=0.00001))
        await asyncio.sleep(0.1)
        loop.call_soon(finish.set_result, None)
        winner, index, excs = await task
        assert len(winners) == 4
        assert winners == [0, 1, 2, 3]
        assert winner == 0
        assert index == 0
        assert excs == [None, None, None, None]

    loop.run_until_complete(run())
