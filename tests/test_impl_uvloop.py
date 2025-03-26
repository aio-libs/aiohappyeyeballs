import asyncio
import socket
from types import ModuleType
from typing import Tuple
from unittest import mock

import pytest

try:
    import uvloop
except ImportError:
    pytest.mark.skip("uvloop is not installed")


from aiohappyeyeballs import (
    start_connection,
)

from .conftest import patch_socket


@pytest.fixture(scope="module")
def event_loop_policy():
    return uvloop.EventLoopPolicy()


@patch_socket
@pytest.mark.asyncio
async def test_uvloop_runtime_error(
    m_socket: ModuleType,
) -> None:
    """
    Test RuntimeError is handled when connecting a socket with uvloop.

    Connecting a socket can raise a RuntimeError, OSError or ValueError.

    - OSError: If the address is invalid or the connection fails.
    - ValueError: if a non-sock it passed (this should never happen).
    https://github.com/python/cpython/blob/e44eebfc1eccdaaebc219accbfc705c9a9de068d/Lib/asyncio/selector_events.py#L271
    - RuntimeError: If the file descriptor is already in use by a transport.

    We should never get ValueError since we are using the correct types.

    selector_events.py never seems to raise a RuntimeError, but it is possible
    with uvloop. This test is to ensure that we handle it correctly.
    """
    mock_socket = mock.MagicMock(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
        fileno=mock.MagicMock(return_value=1),
    )
    create_calls = []

    def _socket(*args, **kw):
        for attr in kw:
            setattr(mock_socket, attr, kw[attr])
        return mock_socket

    async def _sock_connect(
        sock: socket.socket, address: Tuple[str, int, int, int]
    ) -> None:
        create_calls.append(address)
        raise RuntimeError("all fail")

    m_socket.socket = _socket  # type: ignore
    ipv6_addr_info = (
        socket.AF_INET6,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        ("dead:beef::", 80, 0, 0),
    )
    ipv6_addr_info_2 = (
        socket.AF_INET6,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        ("dead:aaaa::", 80, 0, 0),
    )
    ipv4_addr_info = (
        socket.AF_INET,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        ("107.6.106.83", 80),
    )
    addr_info = [ipv6_addr_info, ipv6_addr_info_2, ipv4_addr_info]
    local_addr_infos = [
        (
            socket.AF_INET6,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("::1", 0, 0, 0),
        ),
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("127.0.0.1", 0),
        ),
    ]
    loop = asyncio.get_running_loop()
    # We should get the same exception raised if they are all the same
    with mock.patch.object(loop, "sock_connect", _sock_connect), pytest.raises(
        RuntimeError, match="all fail"
    ):
        assert (
            await start_connection(
                addr_info,
                happy_eyeballs_delay=0.3,
                interleave=2,
                local_addr_infos=local_addr_infos,
            )
            == mock_socket
        )

    # All calls failed
    assert create_calls == [
        ("dead:beef::", 80, 0, 0),
        ("dead:aaaa::", 80, 0, 0),
        ("107.6.106.83", 80),
    ]


@patch_socket
@pytest.mark.asyncio
async def test_uvloop_different_runtime_error(
    m_socket: ModuleType,
) -> None:
    """Test different RuntimeErrors are handled when connecting a socket with uvloop."""
    mock_socket = mock.MagicMock(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
        fileno=mock.MagicMock(return_value=1),
    )
    create_calls = []
    counter = 0

    def _socket(*args, **kw):
        for attr in kw:
            setattr(mock_socket, attr, kw[attr])
        return mock_socket

    async def _sock_connect(
        sock: socket.socket, address: Tuple[str, int, int, int]
    ) -> None:
        create_calls.append(address)
        nonlocal counter
        counter += 1
        raise RuntimeError(counter)

    m_socket.socket = _socket  # type: ignore
    ipv6_addr_info = (
        socket.AF_INET6,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        ("dead:beef::", 80, 0, 0),
    )
    ipv6_addr_info_2 = (
        socket.AF_INET6,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        ("dead:aaaa::", 80, 0, 0),
    )
    ipv4_addr_info = (
        socket.AF_INET,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        ("107.6.106.83", 80),
    )
    addr_info = [ipv6_addr_info, ipv6_addr_info_2, ipv4_addr_info]
    local_addr_infos = [
        (
            socket.AF_INET6,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("::1", 0, 0, 0),
        ),
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("127.0.0.1", 0),
        ),
    ]
    loop = asyncio.get_running_loop()
    # We should get the same exception raised if they are all the same
    with mock.patch.object(loop, "sock_connect", _sock_connect), pytest.raises(
        RuntimeError, match="Multiple exceptions: 1, 2, 3"
    ):
        assert (
            await start_connection(
                addr_info,
                happy_eyeballs_delay=0.3,
                interleave=2,
                local_addr_infos=local_addr_infos,
            )
            == mock_socket
        )

    # All calls failed
    assert create_calls == [
        ("dead:beef::", 80, 0, 0),
        ("dead:aaaa::", 80, 0, 0),
        ("107.6.106.83", 80),
    ]


@patch_socket
@pytest.mark.asyncio
async def test_uvloop_mixing_os_and_runtime_error(
    m_socket: ModuleType,
) -> None:
    """Test uvloop raising OSError and RuntimeError."""
    mock_socket = mock.MagicMock(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
        fileno=mock.MagicMock(return_value=1),
    )
    create_calls = []
    counter = 0

    def _socket(*args, **kw):
        for attr in kw:
            setattr(mock_socket, attr, kw[attr])
        return mock_socket

    async def _sock_connect(
        sock: socket.socket, address: Tuple[str, int, int, int]
    ) -> None:
        create_calls.append(address)
        nonlocal counter
        counter += 1
        if counter == 1:
            raise RuntimeError(counter)
        raise OSError(counter, f"all fail {counter}")

    m_socket.socket = _socket  # type: ignore
    ipv6_addr_info = (
        socket.AF_INET6,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        ("dead:beef::", 80, 0, 0),
    )
    ipv6_addr_info_2 = (
        socket.AF_INET6,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        ("dead:aaaa::", 80, 0, 0),
    )
    ipv4_addr_info = (
        socket.AF_INET,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        ("107.6.106.83", 80),
    )
    addr_info = [ipv6_addr_info, ipv6_addr_info_2, ipv4_addr_info]
    local_addr_infos = [
        (
            socket.AF_INET6,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("::1", 0, 0, 0),
        ),
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("127.0.0.1", 0),
        ),
    ]
    loop = asyncio.get_running_loop()
    # We should get the same exception raised if they are all the same
    with mock.patch.object(loop, "sock_connect", _sock_connect), pytest.raises(
        OSError, match="Multiple exceptions: 1"
    ):
        assert (
            await start_connection(
                addr_info,
                happy_eyeballs_delay=0.3,
                interleave=2,
                local_addr_infos=local_addr_infos,
            )
            == mock_socket
        )

    # All calls failed
    assert create_calls == [
        ("dead:beef::", 80, 0, 0),
        ("dead:aaaa::", 80, 0, 0),
        ("107.6.106.83", 80),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "connect_side_effect",
    [
        OSError("during connect"),
        asyncio.CancelledError("during connect"),
    ],
)
@patch_socket
async def test_single_addr_info_close_errors_uvloop(
    m_socket: ModuleType, connect_side_effect: BaseException
) -> None:
    mock_socket = mock.MagicMock(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
        fileno=mock.MagicMock(return_value=1),
    )
    mock_socket.configure_mock(
        **{
            "connect.side_effect": connect_side_effect,
            "close.side_effect": OSError("during close"),
        }
    )

    def _socket(*args, **kw):
        return mock_socket

    m_socket.socket = _socket  # type: ignore

    addr_info = [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("107.6.106.82", 80),
        )
    ]
    with pytest.raises(OSError, match="during close"):
        await start_connection(addr_info)
