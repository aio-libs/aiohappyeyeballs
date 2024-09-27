import asyncio
import contextlib
from typing import Awaitable, Callable, Iterable, List, Optional, Tuple, TypeVar


class _Done(Exception):
    pass


_T = TypeVar("_T")


async def staggered_race(
    coro_fns: Iterable[Callable[[], Awaitable[_T]]], delay: Optional[float]
) -> Tuple[Optional[_T], Optional[int], List[Optional[BaseException]]]:
    """
    Run coroutines with staggered start times and take the first to finish.

    This method takes an iterable of coroutine functions. The first one is
    started immediately. From then on, whenever the immediately preceding one
    fails (raises an exception), or when *delay* seconds has passed, the next
    coroutine is started. This continues until one of the coroutines complete
    successfully, in which case all others are cancelled, or until all
    coroutines fail.

    The coroutines provided should be well-behaved in the following way:

    * They should only ``return`` if completed successfully.

    * They should always raise an exception if they did not complete
      successfully. In particular, if they handle cancellation, they should
      probably reraise, like this::

        try:
            # do work
        except asyncio.CancelledError:
            # undo partially completed work
            raise

    Args:
        coro_fns: an iterable of coroutine functions, i.e. callables that
            return a coroutine object when called. Use ``functools.partial`` or
            lambdas to pass arguments.

        delay: amount of time, in seconds, between starting coroutines. If
            ``None``, the coroutines will run sequentially.

    Returns:
        tuple *(winner_result, winner_index, exceptions)* where

        - *winner_result*: the result of the winning coroutine, or ``None``
          if no coroutines won.

        - *winner_index*: the index of the winning coroutine in
          ``coro_fns``, or ``None`` if no coroutines won. If the winning
          coroutine may return None on success, *winner_index* can be used
          to definitively determine whether any coroutine won.

        - *exceptions*: list of exceptions returned by the coroutines.
          ``len(exceptions)`` is equal to the number of coroutines actually
          started, and the order is the same as in ``coro_fns``. The winning
          coroutine's entry is ``None``.

    """
    # TODO: when we have aiter() and anext(), allow async iterables in coro_fns.
    winner_result = None
    winner_index = None
    exceptions: List[Optional[BaseException]] = []

    async def run_one_coro(
        this_index: int,
        coro_fn: Callable[[], Awaitable[_T]],
        this_failed: asyncio.Event,
    ) -> None:
        try:
            result = await coro_fn()
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            exceptions[this_index] = e
            this_failed.set()  # Kickstart the next coroutine
        else:
            # Store winner's results
            nonlocal winner_index, winner_result
            assert winner_index is None  # noqa: S101
            winner_index = this_index
            winner_result = result
            raise _Done

    try:
        async with asyncio.TaskGroup() as tg:
            for this_index, coro_fn in enumerate(coro_fns):
                this_failed = asyncio.Event()
                exceptions.append(None)
                tg.create_task(run_one_coro(this_index, coro_fn, this_failed))
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(this_failed.wait(), delay)
    except* _Done:
        pass

    return winner_result, winner_index, exceptions
