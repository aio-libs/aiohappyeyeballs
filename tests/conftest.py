"""Configuration for the tests."""

import asyncio
import reprlib
import socket
import threading
from asyncio.events import AbstractEventLoop, TimerHandle
from contextlib import contextmanager
from typing import Generator
from unittest import mock

import pytest


def mock_nonblocking_socket(
    proto=socket.IPPROTO_TCP, type=socket.SOCK_STREAM, family=socket.AF_INET
):
    """Create a mock of a non-blocking socket."""
    sock = mock.create_autospec(socket.socket, spec_set=True, instance=True)
    sock.proto = proto
    sock.type = type
    sock.family = family
    sock.gettimeout.return_value = 0.0
    return sock


def mock_socket_module():
    m_socket = mock.MagicMock(spec=socket)
    for name in (
        "AF_INET",
        "AF_INET6",
        "AF_UNSPEC",
        "IPPROTO_TCP",
        "IPPROTO_UDP",
        "SOCK_STREAM",
        "SOCK_DGRAM",
        "SOL_SOCKET",
        "SO_REUSEADDR",
        "inet_pton",
    ):
        if hasattr(socket, name):
            setattr(m_socket, name, getattr(socket, name))
        else:
            delattr(m_socket, name)

    m_socket.socket = mock.MagicMock()
    m_socket.socket.return_value = mock_nonblocking_socket()

    return m_socket


def patch_socket(f):
    return mock.patch("aiohappyeyeballs.impl.socket", new_callable=mock_socket_module)(
        f
    )


@pytest.fixture(autouse=True)
def verify_threads_ended() -> Generator[None, None, None]:
    """Verify that the threads are not running after the test."""
    threads_before = frozenset(threading.enumerate())
    yield
    threads = frozenset(threading.enumerate()) - threads_before
    assert not threads


def get_scheduled_timer_handles(loop: AbstractEventLoop) -> list[TimerHandle]:
    """Return a list of scheduled TimerHandles."""
    if not hasattr(loop, "_scheduled"):
        return []
    handles: list[TimerHandle] = loop._scheduled
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
