import socket
from test.test_asyncio import utils as test_utils
from types import ModuleType
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
    addr_info = [(2, 1, 6, "", ("107.6.106.82", 80))]
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
    addr_info = [(2, 1, 6, "", ("107.6.106.82", 80))]
    assert await create_connection(addr_info) == mock_socket
