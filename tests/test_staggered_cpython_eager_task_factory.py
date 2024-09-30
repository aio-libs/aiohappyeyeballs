"""
Tests staggered_race and eager_task_factory with asyncio.Task.

These tests are copied from cpython to ensure our implementation is
compatible with the one in cpython.
"""

import asyncio
import sys
import unittest

from aiohappyeyeballs._staggered import staggered_race


def tearDownModule():
    asyncio.set_event_loop_policy(None)


class EagerTaskFactoryLoopTests(unittest.TestCase):
    def close_loop(self, loop):
        loop.close()

    def set_event_loop(self, loop, *, cleanup=True):
        if loop is None:
            raise AssertionError("loop is None")
        # ensure that the event loop is passed explicitly in asyncio
        asyncio.set_event_loop(None)
        if cleanup:
            self.addCleanup(self.close_loop, loop)

    def tearDown(self):
        asyncio.set_event_loop(None)
        self.doCleanups()

    def setUp(self):
        if sys.version_info < (3, 12):
            self.skipTest("eager_task_factory is only available in Python 3.12+")

        super().setUp()
        self.loop = asyncio.new_event_loop()
        self.eager_task_factory = asyncio.create_eager_task_factory(asyncio.Task)
        self.loop.set_task_factory(self.eager_task_factory)
        self.set_event_loop(self.loop)

    def test_staggered_race_with_eager_tasks(self):
        # See https://github.com/python/cpython/issues/124309

        async def fail():
            await asyncio.sleep(0)
            raise ValueError("no good")

        async def run():
            winner, index, excs = await staggered_race(
                [
                    lambda: asyncio.sleep(2, result="sleep2"),
                    lambda: asyncio.sleep(1, result="sleep1"),
                    lambda: fail(),
                ],
                delay=0.25,
            )
            self.assertEqual(winner, "sleep1")
            self.assertEqual(index, 1)
            assert index is not None
            self.assertIsNone(excs[index])
            self.assertIsInstance(excs[0], asyncio.CancelledError)
            self.assertIsInstance(excs[2], ValueError)

        self.loop.run_until_complete(run())

    def test_staggered_race_with_eager_tasks_no_delay(self):
        # See https://github.com/python/cpython/issues/124309
        async def fail():
            raise ValueError("no good")

        async def run():
            winner, index, excs = await staggered_race(
                [
                    lambda: fail(),
                    lambda: asyncio.sleep(1, result="sleep1"),
                    lambda: asyncio.sleep(0, result="sleep0"),
                ],
                delay=None,
            )
            self.assertEqual(winner, "sleep1")
            self.assertEqual(index, 1)
            assert index is not None
            self.assertIsNone(excs[index])
            self.assertIsInstance(excs[0], ValueError)
            self.assertEqual(len(excs), 2)

        self.loop.run_until_complete(run())


if __name__ == "__main__":
    if sys.version_info >= (3, 12):
        unittest.main()
