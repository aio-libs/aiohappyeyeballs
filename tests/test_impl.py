import asyncio
import socket
from types import ModuleType
from typing import List, Optional, Sequence, Set, Tuple, Union
from unittest import mock

import pytest

from aiohappyeyeballs import (
    AddrInfoType,
    SocketFactoryType,
    _staggered,
    impl,
    start_connection,
)


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


def patch_socket(f):
    return mock.patch("aiohappyeyeballs.impl.socket", new_callable=mock_socket_module)(
        f
    )


@pytest.mark.asyncio
@patch_socket
async def test_single_addr_info_errors(m_socket: ModuleType) -> None:
    idx = -1
    errors = ["err1", "err2"]

    def _socket(*args, **kw):
        nonlocal idx, errors
        idx += 1
        raise OSError(5, errors[idx])

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
        await start_connection(addr_info)


@pytest.mark.asyncio
@patch_socket
async def test_single_addr_success(m_socket: ModuleType) -> None:
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
        assert await start_connection(addr_info) == mock_socket


@pytest.mark.asyncio
@patch_socket
async def test_single_addr_success_passing_loop(m_socket: ModuleType) -> None:
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
        assert (
            await start_connection(addr_info, loop=asyncio.get_running_loop())
            == mock_socket
        )


@pytest.mark.asyncio
@patch_socket
async def test_single_addr_socket_factory(m_socket: ModuleType) -> None:
    mock_socket = mock.MagicMock(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
        fileno=mock.MagicMock(return_value=1),
    )

    def factory(addr_info: AddrInfoType) -> socket.socket:
        return mock_socket

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
        assert await start_connection(addr_info, socket_factory=factory) == mock_socket


@pytest.mark.asyncio
@patch_socket
async def test_multiple_addr_success_second_one(
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
            raise OSError(5, errors[idx])
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
        assert await start_connection(addr_info) == mock_socket


@pytest.mark.asyncio
@patch_socket
async def test_multiple_winners_cleaned_up(
    m_socket: ModuleType,
) -> None:
    loop = asyncio.get_running_loop()
    finish = loop.create_future()

    def _socket(*args, **kw):
        return mock.MagicMock(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
            fileno=mock.MagicMock(return_value=1),
        )

    async def _connect_sock(
        loop: asyncio.AbstractEventLoop,
        exceptions: List[List[Union[OSError, RuntimeError]]],
        addr_info: AddrInfoType,
        local_addr_infos: Optional[Sequence[AddrInfoType]] = None,
        sockets: Optional[Set[socket.socket]] = None,
        socket_factory: Optional[SocketFactoryType] = None,
    ) -> socket.socket:
        await finish
        sock = _socket()
        assert sockets is not None
        sockets.add(sock)
        return sock

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
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("107.6.106.84", 80),
        ),
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("107.6.106.85", 80),
        ),
    ]
    with mock.patch.object(impl, "_connect_sock", _connect_sock):
        task = loop.create_task(
            start_connection(addr_info, happy_eyeballs_delay=0.0001, interleave=0)
        )
        await asyncio.sleep(0.1)
        loop.call_soon(finish.set_result, None)
        await task


@pytest.mark.asyncio
@patch_socket
async def test_multiple_addr_success_second_one_happy_eyeballs(
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
            raise OSError(5, errors[idx])
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
            await start_connection(addr_info, happy_eyeballs_delay=0.3) == mock_socket
        )


@pytest.mark.asyncio
@patch_socket
async def test_happy_eyeballs_socket_factory(
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

    def factory(addr_info: AddrInfoType) -> socket.socket:
        nonlocal idx, errors
        idx += 1
        if idx == 1:
            raise OSError(5, errors[idx])
        return mock_socket

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
            await start_connection(
                addr_info, happy_eyeballs_delay=0.3, socket_factory=factory
            )
            == mock_socket
        )


@pytest.mark.asyncio
@patch_socket
async def test_multiple_addr_all_fail_happy_eyeballs(
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
        raise OSError(5, errors[idx])

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
        await start_connection(addr_info, happy_eyeballs_delay=0.3)


@pytest.mark.asyncio
@patch_socket
async def test_ipv6_and_ipv4_happy_eyeballs_ipv6_fails(
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
            raise OSError(5, "ipv6 fail")
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
            await start_connection(addr_info, happy_eyeballs_delay=0.3) == mock_socket
        )
    assert mock_socket.family == socket.AF_INET


@pytest.mark.asyncio
@patch_socket
async def test_ipv6_and_ipv4_happy_eyeballs_ipv4_fails(
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
            raise OSError(5, "ipv4 fail")
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
            await start_connection(addr_info, happy_eyeballs_delay=0.3) == mock_socket
        )
    assert mock_socket.family == socket.AF_INET6


@pytest.mark.asyncio
@patch_socket
async def test_ipv6_and_ipv4_happy_eyeballs_first_ipv6_fails(
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
            raise OSError(5, "ipv6 fail")

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
            await start_connection(addr_info, happy_eyeballs_delay=0.3) == mock_socket
        )

    # IPv6 addresses are tried first, but the first one fails so IPv4 wins
    assert mock_socket.family == socket.AF_INET
    assert create_calls == [("dead:beef::", 80, 0, 0), ("107.6.106.83", 80)]


@pytest.mark.asyncio
@patch_socket
async def test_ipv64_happy_eyeballs_interleave_2_first_ipv6_fails(
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
            raise OSError(5, "ipv6 fail")

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
            await start_connection(addr_info, happy_eyeballs_delay=0.3, interleave=2)
            == mock_socket
        )

    # IPv6 addresses are tried first, but the first one fails so second IPv6 wins
    # because interleave is 2
    assert mock_socket.family == socket.AF_INET6
    assert create_calls == [("dead:beef::", 80, 0, 0), ("dead:aaaa::", 80, 0, 0)]


@pytest.mark.asyncio
@patch_socket
async def test_ipv6_only_happy_eyeballs_first_ipv6_fails(
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
            raise OSError(5, "ipv6 fail")

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
            await start_connection(addr_info, happy_eyeballs_delay=0.3) == mock_socket
        )

    # IPv6 address are tried first, but the first one fails so second IPv6 wins
    assert mock_socket.family == socket.AF_INET6
    assert create_calls == [("dead:beef::", 80, 0, 0), ("dead:aaaa::", 80, 0, 0)]


@pytest.mark.asyncio
@patch_socket
async def test_ipv64_laddr_eyeballs_interleave_2_first_ipv6_fails(
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
            raise OSError(5, "ipv6 fail")

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
    local_addr_infos = [
        (
            socket.AF_INET6,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("::1", 0, 0, 0),
        )
    ]
    loop = asyncio.get_running_loop()
    with mock.patch.object(loop, "sock_connect", _sock_connect):
        assert (
            await start_connection(
                addr_info,
                happy_eyeballs_delay=0.3,
                interleave=2,
                local_addr_infos=local_addr_infos,
            )
            == mock_socket
        )

    # IPv6 addresses are tried first, but the first one fails so second IPv6 wins
    # because interleave is 2
    assert mock_socket.family == socket.AF_INET6
    assert create_calls == [("dead:beef::", 80, 0, 0), ("dead:aaaa::", 80, 0, 0)]


@pytest.mark.asyncio
@patch_socket
async def test_ipv64_laddr_both__eyeballs_first_ipv6_fails(
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
            raise OSError(5, "ipv6 fail")

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
    with mock.patch.object(loop, "sock_connect", _sock_connect):
        assert (
            await start_connection(
                addr_info,
                happy_eyeballs_delay=0.3,
                local_addr_infos=local_addr_infos,
            )
            == mock_socket
        )

    # IPv6 is tried first and fails, which means IPv4 is tried next and succeeds
    assert mock_socket.family == socket.AF_INET
    assert create_calls == [("dead:beef::", 80, 0, 0), ("107.6.106.83", 80)]


@pytest.mark.asyncio
@patch_socket
async def test_ipv64_laddr_bind_fails_eyeballs_first_ipv6_fails(
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
        if kw["family"] == socket.AF_INET:
            mock_socket.bind.side_effect = OSError(5, "bind fail")

        return mock_socket

    async def _sock_connect(
        sock: socket.socket, address: Tuple[str, int, int, int]
    ) -> None:
        create_calls.append(address)
        if address[0] == "dead:beef::":
            raise OSError(5, "ipv6 fail")

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
    with mock.patch.object(loop, "sock_connect", _sock_connect), pytest.raises(
        OSError, match="ipv6 fail"
    ):
        assert (
            await start_connection(
                addr_info,
                happy_eyeballs_delay=0.3,
                interleave=1,
                local_addr_infos=local_addr_infos,
            )
            == mock_socket
        )

    # We only tried IPv6 since bind to IPv4 failed
    assert create_calls == [("dead:beef::", 80, 0, 0)]


@pytest.mark.asyncio
@patch_socket
async def test_ipv64_laddr_bind_fails_eyeballs_interleave_first__ipv6_fails(
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
        if kw["family"] == socket.AF_INET:
            mock_socket.bind.side_effect = OSError(5, "bind fail")

        return mock_socket

    async def _sock_connect(
        sock: socket.socket, address: Tuple[str, int, int, int]
    ) -> None:
        create_calls.append(address)
        if address[0] == "dead:beef::":
            raise OSError(5, "ipv6 fail")

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
    with mock.patch.object(loop, "sock_connect", _sock_connect):
        assert (
            await start_connection(
                addr_info,
                happy_eyeballs_delay=0.3,
                interleave=2,
                local_addr_infos=local_addr_infos,
            )
            == mock_socket
        )

    # IPv6 is tried first and fails, which means IPv4 is tried next but the laddr
    # build fails so we move on to the next IPv6 and it succeeds
    assert create_calls == [("dead:beef::", 80, 0, 0), ("dead:aaaa::", 80, 0, 0)]
    assert mock_socket.family == socket.AF_INET6


@pytest.mark.asyncio
@patch_socket
async def test_ipv64_laddr_socket_fails(
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
        raise Exception("Something really went wrong")

    async def _sock_connect(
        sock: socket.socket, address: Tuple[str, int, int, int]
    ) -> None:
        create_calls.append(address)
        if address[0] == "dead:beef::":
            raise OSError(5, "ipv6 fail")

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
    with mock.patch.object(loop, "sock_connect", _sock_connect), pytest.raises(
        Exception, match="Something really went wrong"
    ):
        assert (
            await start_connection(
                addr_info,
                local_addr_infos=local_addr_infos,
            )
            == mock_socket
        )

    # All binds failed
    assert create_calls == []


@pytest.mark.asyncio
@patch_socket
async def test_ipv64_laddr_socket_blocking_fails(
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
        mock_socket.setblocking.side_effect = Exception("Something really went wrong")
        return mock_socket

    async def _sock_connect(
        sock: socket.socket, address: Tuple[str, int, int, int]
    ) -> None:
        create_calls.append(address)
        if address[0] == "dead:beef::":
            raise OSError(5, "ipv6 fail")

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
    with mock.patch.object(loop, "sock_connect", _sock_connect), pytest.raises(
        Exception, match="Something really went wrong"
    ):
        assert (
            await start_connection(
                addr_info,
                local_addr_infos=local_addr_infos,
            )
            == mock_socket
        )

    # All binds failed
    assert create_calls == []


@pytest.mark.asyncio
@patch_socket
async def test_ipv64_laddr_eyeballs_ipv4_only_tried(
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
            raise OSError(5, "ipv6 fail")

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
    local_addr_infos = [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("127.0.0.1", 0),
        )
    ]
    loop = asyncio.get_running_loop()
    with mock.patch.object(loop, "sock_connect", _sock_connect):
        assert (
            await start_connection(
                addr_info,
                happy_eyeballs_delay=0.3,
                interleave=2,
                local_addr_infos=local_addr_infos,
            )
            == mock_socket
        )

    # Only IPv4 addresses are tried because local_addr_infos is IPv4
    assert mock_socket.family == socket.AF_INET
    assert create_calls == [("107.6.106.83", 80)]


@patch_socket
@pytest.mark.asyncio
async def test_ipv64_laddr_bind_fails_all_eyeballs_interleave_first__ipv6_fails(
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
        mock_socket.bind.side_effect = OSError(4, "bind fail")
        return mock_socket

    async def _sock_connect(
        sock: socket.socket, address: Tuple[str, int, int, int]
    ) -> None:
        create_calls.append(address)
        if address[0] == "dead:beef::":
            raise OSError(5, "ipv6 fail")

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
    with mock.patch.object(loop, "sock_connect", _sock_connect), pytest.raises(
        OSError, match="Multiple exceptions"
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

    # All binds failed
    assert create_calls == []


@patch_socket
@pytest.mark.asyncio
async def test_all_same_exception_and_same_errno(
    m_socket: ModuleType,
) -> None:
    """Test that all exceptions are the same and have the same errno."""
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
        raise OSError(5, "all fail")

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
        OSError, match="all fail"
    ) as exc_info:
        assert (
            await start_connection(
                addr_info,
                happy_eyeballs_delay=0.3,
                interleave=2,
                local_addr_infos=local_addr_infos,
            )
            == mock_socket
        )

    assert exc_info.value.errno == 5

    # All calls failed
    assert create_calls == [
        ("dead:beef::", 80, 0, 0),
        ("dead:aaaa::", 80, 0, 0),
        ("107.6.106.83", 80),
    ]


@patch_socket
@pytest.mark.asyncio
async def test_all_same_exception_and_with_different_errno(
    m_socket: ModuleType,
) -> None:
    """Test no errno is set if all OSError have different errno."""
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
        raise OSError(len(create_calls), "all fail")

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
        OSError, match="all fail"
    ) as exc_info:
        assert (
            await start_connection(
                addr_info,
                happy_eyeballs_delay=0.3,
                interleave=2,
                local_addr_infos=local_addr_infos,
            )
            == mock_socket
        )

    # No errno is set if they are all different
    assert exc_info.value.errno is None

    # All calls failed
    assert create_calls == [
        ("dead:beef::", 80, 0, 0),
        ("dead:aaaa::", 80, 0, 0),
        ("107.6.106.83", 80),
    ]


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


@patch_socket
@pytest.mark.asyncio
async def test_handling_system_exit(
    m_socket: ModuleType,
) -> None:
    """Test handling SystemExit."""

    class MockSystemExit(BaseException):
        """Mock SystemExit."""

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
        raise MockSystemExit

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
    with pytest.raises(MockSystemExit), mock.patch.object(
        loop, "sock_connect", _sock_connect
    ), mock.patch.object(_staggered, "RE_RAISE_EXCEPTIONS", (MockSystemExit,)):
        await start_connection(
            addr_info,
            happy_eyeballs_delay=0.3,
            interleave=2,
            local_addr_infos=local_addr_infos,
        )

    # Stopped after the first call
    assert create_calls == [
        ("dead:beef::", 80, 0, 0),
    ]


@patch_socket
@pytest.mark.asyncio
async def test_cancellation_is_not_swallowed(
    m_socket: ModuleType,
) -> None:
    """Test that cancellation is not swallowed."""
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
        await asyncio.sleep(1000)

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
        asyncio.CancelledError
    ):
        task = asyncio.create_task(
            start_connection(
                addr_info,
                happy_eyeballs_delay=0.3,
                interleave=2,
                local_addr_infos=local_addr_infos,
            )
        )
        await asyncio.sleep(0)
        task.cancel()
        await task

    # After calls are cancelled now more are made
    assert create_calls == [
        ("dead:beef::", 80, 0, 0),
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
async def test_single_addr_info_close_errors(
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
