import asyncio
from typing import (
    Any,
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


def _set_result_if_not_done(fut: asyncio.Future[None]) -> None:
    """Set the result of a future if it is not already done."""
    if not fut.done():
        fut.set_result(None)


async def staggered_race(
    coro_fns: Iterable[Callable[[], Awaitable[_T]]],
    delay: float,
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
    winner_future: asyncio.Future[Tuple[_T, int]] = loop.create_future()
    exceptions: List[Optional[BaseException]] = []
    tasks: Set[asyncio.Task[None]] = set()

    async def run_one_coro(
        coro_fn: Callable[[], Awaitable[_T]],
        this_index: int,
        wakeup_next: Optional[asyncio.Future[None]],
    ) -> None:
        try:
            result = await coro_fn()
        except (SystemExit, KeyboardInterrupt) as ex:
            winner_future.set_exception(ex)
        except BaseException as ex:
            exceptions[this_index] = ex
            if wakeup_next:
                _set_result_if_not_done(wakeup_next)
        else:
            winner_future.set_result((result, this_index))

    timer: Optional[asyncio.TimerHandle] = None
    to_run = list(coro_fns)
    last_index = len(to_run) - 1
    try:
        for this_index, coro_fn in enumerate(to_run):
            if this_index != last_index:
                wakeup_next: Optional[asyncio.Future[None]] = loop.create_future()
            else:
                wakeup_next = None
            task: asyncio.Task[None] = loop.create_task(
                run_one_coro(coro_fn, this_index, wakeup_next)
            )
            if winner_future.done():
                # Eager start, task already done
                return *winner_future.result(), exceptions

            tasks.add(task)
            task.add_done_callback(tasks.discard)
            if delay and wakeup_next:
                timer = loop.call_later(delay, _set_result_if_not_done, wakeup_next)

            while tasks:
                waiter: List[Union[asyncio.Future[Any], asyncio.Task[Any]]] = [
                    winner_future,
                    *tasks,
                ]
                if wakeup_next:
                    waiter.append(wakeup_next)
                await asyncio.wait(waiter, return_when=asyncio.FIRST_COMPLETED)
                if winner_future.done():
                    if timer:
                        timer.cancel()
                    return *winner_future.result(), exceptions
                if wakeup_next and wakeup_next.done():
                    break
    finally:
        for task in tasks:
            task.cancel()

    return None, None, exceptions
