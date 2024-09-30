"""Configuration for the tests."""

import asyncio
import threading
from typing import Generator

import pytest


@pytest.fixture(autouse=True)
def verify_threads_ended():
    """Verify that the threads are not running after the test."""
    threads_before = frozenset(threading.enumerate())
    yield
    threads = frozenset(threading.enumerate()) - threads_before
    assert not threads


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
