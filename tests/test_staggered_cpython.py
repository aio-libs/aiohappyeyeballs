"""
Tests for staggered_race.

These tests are copied from cpython to ensure our implementation is
compatible with the one in cpython.
"""

import asyncio
import sys
import unittest

import pytest

from aiohappyeyeballs._staggered import staggered_race


def tearDownModule():
    asyncio.set_event_loop_policy(None)


class StaggeredTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty(self):
        winner, index, excs = await staggered_race(
            [],
            delay=None,
        )

        self.assertIs(winner, None)
        self.assertIs(index, None)
        self.assertEqual(excs, [])

    async def test_one_successful(self):
        async def coro(index):
            return f"Res: {index}"

        winner, index, excs = await staggered_race(
            [
                lambda: coro(0),
                lambda: coro(1),
            ],
            delay=None,
        )

        self.assertEqual(winner, "Res: 0")
        self.assertEqual(index, 0)
        self.assertEqual(excs, [None])

    async def test_first_error_second_successful(self):
        async def coro(index):
            if index == 0:
                raise ValueError(index)
            return f"Res: {index}"

        winner, index, excs = await staggered_race(
            [
                lambda: coro(0),
                lambda: coro(1),
            ],
            delay=None,
        )

        self.assertEqual(winner, "Res: 1")
        self.assertEqual(index, 1)
        self.assertEqual(len(excs), 2)
        self.assertIsInstance(excs[0], ValueError)
        self.assertIs(excs[1], None)

    async def test_first_timeout_second_successful(self):
        async def coro(index):
            if index == 0:
                await asyncio.sleep(10)  # much bigger than delay
            return f"Res: {index}"

        winner, index, excs = await staggered_race(
            [
                lambda: coro(0),
                lambda: coro(1),
            ],
            delay=0.1,
        )

        self.assertEqual(winner, "Res: 1")
        self.assertEqual(index, 1)
        self.assertEqual(len(excs), 2)
        self.assertIsInstance(excs[0], asyncio.CancelledError)
        self.assertIs(excs[1], None)

    async def test_none_successful(self):
        async def coro(index):
            raise ValueError(index)

        for delay in [None, 0, 0.1, 1]:
            with self.subTest(delay=delay):
                winner, index, excs = await staggered_race(
                    [
                        lambda: coro(0),
                        lambda: coro(1),
                    ],
                    delay=delay,
                )

                self.assertIs(winner, None)
                self.assertIs(index, None)
                self.assertEqual(len(excs), 2)
                self.assertIsInstance(excs[0], ValueError)
                self.assertIsInstance(excs[1], ValueError)

    async def test_long_delay_early_failure(self):
        async def coro(index):
            await asyncio.sleep(0)  # Dummy coroutine for the 1 case
            if index == 0:
                await asyncio.sleep(0.1)  # Dummy coroutine
                raise ValueError(index)

            return f"Res: {index}"

        winner, index, excs = await staggered_race(
            [
                lambda: coro(0),
                lambda: coro(1),
            ],
            delay=10,
        )

        self.assertEqual(winner, "Res: 1")
        self.assertEqual(index, 1)
        self.assertEqual(len(excs), 2)
        self.assertIsInstance(excs[0], ValueError)
        self.assertIsNone(excs[1])

    def test_loop_argument(self):
        loop = asyncio.new_event_loop()

        async def coro():
            self.assertEqual(loop, asyncio.get_running_loop())
            return "coro"

        async def main():
            winner, index, excs = await staggered_race([coro], delay=0.1, loop=loop)

            self.assertEqual(winner, "coro")
            self.assertEqual(index, 0)

        loop.run_until_complete(main())
        loop.close()

    async def test_multiple_winners(self):
        event = asyncio.Event()

        async def coro(index):
            await event.wait()
            return index

        async def do_set():
            event.set()
            await asyncio.Event().wait()

        winner, index, excs = await staggered_race(
            [
                lambda: coro(0),
                lambda: coro(1),
                do_set,
            ],
            delay=0.1,
        )
        self.assertIs(winner, 0)
        self.assertIs(index, 0)
        self.assertEqual(len(excs), 3)
        self.assertIsNone(excs[0], None)
        self.assertIsInstance(excs[1], asyncio.CancelledError)
        self.assertIsInstance(excs[2], asyncio.CancelledError)

    @pytest.mark.skipif(
        sys.version_info < (3, 11), reason="asyncio.timeout is not available"
    )
    async def test_cancelled(self):
        log = []
        with self.assertRaises(asyncio.TimeoutError):
            async with asyncio.timeout(None) as cs_outer, asyncio.timeout(
                None
            ) as cs_inner:

                async def coro_fn():
                    cs_inner.reschedule(-1)
                    await asyncio.sleep(0)
                    try:
                        await asyncio.sleep(0)
                    except asyncio.CancelledError:
                        log.append("cancelled 1")

                    cs_outer.reschedule(-1)
                    await asyncio.sleep(0)
                    try:
                        await asyncio.sleep(0)
                    except asyncio.CancelledError:
                        log.append("cancelled 2")

                try:
                    await staggered_race([coro_fn], delay=None)
                except asyncio.CancelledError:
                    log.append("cancelled 3")
                    raise

        self.assertListEqual(log, ["cancelled 1", "cancelled 2", "cancelled 3"])


if __name__ == "__main__":
    unittest.main()
