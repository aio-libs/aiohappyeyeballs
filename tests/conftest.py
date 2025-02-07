"""Configuration for the tests."""

import asyncio
import reprlib
import threading
from asyncio.events import AbstractEventLoop, TimerHandle
from contextlib import contextmanager
from typing import Generator

import pytest


@pytest.fixture(autouse=True)
def verify_threads_ended() -> Generator[None, None, None]:
    """Verify that the threads are not running after the test."""
    threads_before = frozenset(threading.enumerate())
    yield
    threads = frozenset(threading.enumerate()) - threads_before
    assert not threads


def get_scheduled_timer_handles(loop: AbstractEventLoop) -> list[TimerHandle]:
    """Return a list of scheduled TimerHandles."""
    handles: list[TimerHandle] = loop._scheduled  # type: ignore[attr-defined]
    return handles


@contextmanager
def long_repr_strings() -> Generator[None, None, None]:
    """Increase reprlib maxstring and maxother to 300."""
    arepr = reprlib.aRepr
    original_maxstring = arepr.maxstring
    original_maxother = arepr.maxother
    arepr.maxstring = 300
    arepr.maxother = 300
    try:
        yield
    finally:
        arepr.maxstring = original_maxstring
        arepr.maxother = original_maxother


@pytest.fixture(autouse=True)
def verify_no_lingering_tasks(
    event_loop: asyncio.AbstractEventLoop,
) -> Generator[None, None, None]:
    """Verify that all tasks are cleaned up."""
    tasks_before = asyncio.all_tasks(event_loop)
    yield

    tasks = asyncio.all_tasks(event_loop) - tasks_before
    for task in tasks:
        pytest.fail(f"Task still running: {task!r}")
        task.cancel()
    if tasks:
        event_loop.run_until_complete(asyncio.wait(tasks))

    for handle in get_scheduled_timer_handles(event_loop):
        if not handle.cancelled():
            with long_repr_strings():
                pytest.fail(f"Lingering timer after test {handle!r}")
                handle.cancel()
