import asyncio
import contextlib
from functools import partial
from typing import (
    TYPE_CHECKING,
    Awaitable,
    Callable,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)

_T = TypeVar("_T")
_R = TypeVar("_R")


def _set_result(fut: "asyncio.Future[None]") -> None:
    """Set the result of a future if it is not already done."""
    if not fut.done():
        fut.set_result(None)


def _on_completion(wait_next: "asyncio.Future[_R]", done: _R) -> None:
    if not wait_next.done():
        wait_next.set_result(done)


async def staggered_race(
    coro_fns: Iterable[Callable[[], Awaitable[_T]]],
    delay: Optional[float],
    *,
    loop: Optional[asyncio.AbstractEventLoop] = None,
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
    ----
        coro_fns: an iterable of coroutine functions, i.e. callables that
            return a coroutine object when called. Use ``functools.partial`` or
            lambdas to pass arguments.

        delay: amount of time, in seconds, between starting coroutines. If
            ``None``, the coroutines will run sequentially.

        loop: the event loop to use. If ``None``, the running loop is used.

    Returns:
    -------
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
    loop = loop or asyncio.get_running_loop()
    exceptions: List[Optional[BaseException]] = []
    tasks: Set[asyncio.Task[Optional[Tuple[_T, int]]]] = set()

    async def run_one_coro(
        coro_fn: Callable[[], Awaitable[_T]],
        this_index: int,
        wakeup_next: Optional["asyncio.Future[None]"],
    ) -> Optional[Tuple[_T, int]]:
        try:
            result = await coro_fn()
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as ex:
            exceptions[this_index] = ex
            if wakeup_next:
                _set_result(wakeup_next)
            return None

        return result, this_index

    start_next_timer: Optional[asyncio.TimerHandle] = None
    wakeup_next: Optional[asyncio.Future[None]]
    task: asyncio.Task[Optional[Tuple[_T, int]]]
    wait_next: asyncio.Future[
        Union[asyncio.Future[None], asyncio.Task[Optional[Tuple[_T, int]]]]
    ]
    to_run = list(coro_fns)
    last_index = len(to_run) - 1
    try:
        for this_index, coro_fn in enumerate(to_run):
            exceptions.append(None)
            wakeup_next = None if this_index == last_index else loop.create_future()

            tasks.add(loop.create_task(run_one_coro(coro_fn, this_index, wakeup_next)))
            if delay and wakeup_next:
                start_next_timer = loop.call_later(delay, _set_result, wakeup_next)
            else:
                start_next_timer = None

            while tasks:
                wait_next = loop.create_future()
                _on_completion_w_future = partial(_on_completion, wait_next)

                if wakeup_next:
                    wakeup_next.add_done_callback(_on_completion_w_future)
                for t in tasks:
                    t.add_done_callback(_on_completion_w_future)

                try:
                    done = await wait_next
                finally:
                    if wakeup_next:
                        wakeup_next.remove_done_callback(_on_completion_w_future)
                    for t in tasks:
                        t.remove_done_callback(_on_completion_w_future)

                if done is wakeup_next:
                    # The current task has failed or the timer has expired
                    # so we need to start the next task.
                    if start_next_timer:
                        start_next_timer.cancel()
                    break

                if TYPE_CHECKING:
                    assert isinstance(done, asyncio.Task)

                tasks.discard(done)
                try:
                    if winner := done.result():
                        return *winner, exceptions
                finally:
                    # Make sure the Timer is cancelled if the task is going
                    # to raise KeyboardInterrupt or SystemExit.
                    if start_next_timer:
                        start_next_timer.cancel()

    finally:
        # We either have a winner or a KeyboardInterrupt
        # or SystemExit.
        #
        # If there are any tasks left, cancel them and than
        # wait them so they fill the exceptions list.
        #
        for task in tasks:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    return None, None, exceptions
