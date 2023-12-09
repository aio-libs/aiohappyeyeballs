import asyncio
import socket
from test.test_asyncio import utils as test_utils
from types import ModuleType
from typing import Tuple
from unittest import mock

import pytest

from aiohappyeyeballs import create_connection


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
    m_socket.socket.return_value = test_utils.mock_nonblocking_socket()

    return m_socket


def patch_socket(f):
    return mock.patch("aiohappyeyeballs.impl.socket", new_callable=mock_socket_module)(
        f
    )


@pytest.mark.asyncio
@patch_socket
async def test_create_connection_single_addr_info_errors(m_socket: ModuleType) -> None:
    idx = -1
    errors = ["err1", "err2"]

    def _socket(*args, **kw):
        nonlocal idx, errors
        idx += 1
        raise OSError(errors[idx])

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
    with pytest.raises(OSError, match=errors[0]):
        await create_connection(addr_info)


@pytest.mark.asyncio
@patch_socket
async def test_create_connection_single_addr_success(m_socket: ModuleType) -> None:
    mock_socket = mock.MagicMock(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
        fileno=mock.MagicMock(return_value=1),
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
    loop = asyncio.get_running_loop()
    with mock.patch.object(loop, "sock_connect", return_value=None):
        assert await create_connection(addr_info) == mock_socket


@pytest.mark.asyncio
@patch_socket
async def test_create_connection_multiple_addr_success_second_one(
    m_socket: ModuleType,
) -> None:
    mock_socket = mock.MagicMock(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
        fileno=mock.MagicMock(return_value=1),
    )
    idx = -1
    errors = ["err1", "err2"]

    def _socket(*args, **kw):
        nonlocal idx, errors
        idx += 1
        if idx == 1:
            raise OSError(errors[idx])
        return mock_socket

    m_socket.socket = _socket  # type: ignore
    addr_info = [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("107.6.106.82", 80),
        ),
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("107.6.106.83", 80),
        ),
    ]
    loop = asyncio.get_running_loop()
    with mock.patch.object(loop, "sock_connect", return_value=None):
        assert await create_connection(addr_info) == mock_socket


@pytest.mark.asyncio
@patch_socket
async def test_create_connection_multiple_addr_success_second_one_happy_eyeballs(
    m_socket: ModuleType,
) -> None:
    mock_socket = mock.MagicMock(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
        fileno=mock.MagicMock(return_value=1),
    )
    idx = -1
    errors = ["err1", "err2"]

    def _socket(*args, **kw):
        nonlocal idx, errors
        idx += 1
        if idx == 1:
            raise OSError(errors[idx])
        return mock_socket

    m_socket.socket = _socket  # type: ignore
    addr_info = [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("107.6.106.82", 80),
        ),
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("107.6.106.83", 80),
        ),
    ]
    loop = asyncio.get_running_loop()
    with mock.patch.object(loop, "sock_connect", return_value=None):
        assert (
            await create_connection(addr_info, happy_eyeballs_delay=0.3) == mock_socket
        )


@pytest.mark.asyncio
@patch_socket
async def test_create_connection_multiple_addr_all_fail_happy_eyeballs(
    m_socket: ModuleType,
) -> None:
    mock.MagicMock(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
        fileno=mock.MagicMock(return_value=1),
    )
    idx = -1
    errors = ["err1", "err2"]

    def _socket(*args, **kw):
        nonlocal idx, errors
        idx += 1
        raise OSError(errors[idx])

    m_socket.socket = _socket  # type: ignore
    addr_info = [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("107.6.106.82", 80),
        ),
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("107.6.106.83", 80),
        ),
    ]
    asyncio.get_running_loop()
    with pytest.raises(OSError, match=errors[0]):
        await create_connection(addr_info, happy_eyeballs_delay=0.3)


@pytest.mark.asyncio
@patch_socket
async def test_create_connection_ipv6_and_ipv4_happy_eyeballs_ipv6_fails(
    m_socket: ModuleType,
) -> None:
    mock_socket = mock.MagicMock(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
        fileno=mock.MagicMock(return_value=1),
    )

    def _socket(*args, **kw):
        if kw["family"] == socket.AF_INET6:
            raise OSError("ipv6 fail")
        for attr in kw:
            setattr(mock_socket, attr, kw[attr])
        return mock_socket

    m_socket.socket = _socket  # type: ignore
    ipv6_addr_info = (
        socket.AF_INET6,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        ("dead:beef::", 80, 0, 0),
    )
    ipv4_addr_info = (
        socket.AF_INET,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        ("107.6.106.83", 80),
    )
    addr_info = [ipv6_addr_info, ipv4_addr_info]
    loop = asyncio.get_running_loop()
    with mock.patch.object(loop, "sock_connect", return_value=None):
        assert (
            await create_connection(addr_info, happy_eyeballs_delay=0.3) == mock_socket
        )
    assert mock_socket.family == socket.AF_INET


@pytest.mark.asyncio
@patch_socket
async def test_create_connection_ipv6_and_ipv4_happy_eyeballs_ipv4_fails(
    m_socket: ModuleType,
) -> None:
    mock_socket = mock.MagicMock(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
        fileno=mock.MagicMock(return_value=1),
    )

    def _socket(*args, **kw):
        if kw["family"] == socket.AF_INET:
            raise OSError("ipv4 fail")
        for attr in kw:
            setattr(mock_socket, attr, kw[attr])
        return mock_socket

    m_socket.socket = _socket  # type: ignore
    ipv6_addr: Tuple[str, int, int, int] = ("dead:beef::", 80, 0, 0)
    ipv6_addr_info: Tuple[int, int, int, str, Tuple[str, int, int, int]] = (
        socket.AF_INET6,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        ipv6_addr,
    )
    ipv4_addr: Tuple[str, int] = ("107.6.106.83", 80)
    ipv4_addr_info: Tuple[int, int, int, str, Tuple[str, int]] = (
        socket.AF_INET,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        ipv4_addr,
    )
    addr_info = [ipv6_addr_info, ipv4_addr_info]
    loop = asyncio.get_running_loop()
    with mock.patch.object(loop, "sock_connect", return_value=None):
        assert (
            await create_connection(addr_info, happy_eyeballs_delay=0.3) == mock_socket
        )
    assert mock_socket.family == socket.AF_INET6


@pytest.mark.asyncio
@patch_socket
async def test_create_connection_ipv6_and_ipv4_happy_eyeballs_first_ipv6_fails(
    m_socket: ModuleType,
) -> None:
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
        if address[0] == "dead:beef::":
            raise OSError("ipv6 fail")

        return None

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
    loop = asyncio.get_running_loop()
    with mock.patch.object(loop, "sock_connect", _sock_connect):
        assert (
            await create_connection(addr_info, happy_eyeballs_delay=0.3) == mock_socket
        )

    # IPv6 addresses are tried first, but the first one fails so IPv4 wins
    assert mock_socket.family == socket.AF_INET
    assert create_calls == [("dead:beef::", 80, 0, 0), ("107.6.106.83", 80)]


@pytest.mark.asyncio
@patch_socket
async def test_create_connection_ipv6_only_happy_eyeballs_first_ipv6_fails(
    m_socket: ModuleType,
) -> None:
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
        if address[0] == "dead:beef::":
            raise OSError("ipv6 fail")

        return None

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
    addr_info = [ipv6_addr_info, ipv6_addr_info_2]
    loop = asyncio.get_running_loop()
    with mock.patch.object(loop, "sock_connect", _sock_connect):
        assert (
            await create_connection(addr_info, happy_eyeballs_delay=0.3) == mock_socket
        )

    # IPv6 address are tried first, but the first one fails so second IPv6 wins
    assert mock_socket.family == socket.AF_INET6
    assert create_calls == [("dead:beef::", 80, 0, 0), ("dead:aaaa::", 80, 0, 0)]
