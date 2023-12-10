import socket
from typing import List

import pytest

from aiohappyeyeballs import AddrInfoType, pop_addr_infos_interleave, remove_addr_infos


def test_pop_addr_infos_interleave():
    """Test pop_addr_infos_interleave."""
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
    addr_info: List[AddrInfoType] = [ipv6_addr_info, ipv6_addr_info_2, ipv4_addr_info]
    addr_info_copy = addr_info.copy()
    pop_addr_infos_interleave(addr_info_copy, 1)
    assert addr_info_copy == [ipv6_addr_info_2]
    pop_addr_infos_interleave(addr_info_copy, 1)
    assert addr_info_copy == []
    addr_info_copy = addr_info.copy()
    pop_addr_infos_interleave(addr_info_copy, 2)
    assert addr_info_copy == []


def test_remove_addr_infos():
    """Test remove_addr_infos."""
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
    addr_info: List[AddrInfoType] = [ipv6_addr_info, ipv6_addr_info_2, ipv4_addr_info]
    addr_info_copy = addr_info.copy()
    remove_addr_infos(addr_info_copy, "dead:beef::")
    assert addr_info_copy == [ipv6_addr_info_2, ipv4_addr_info]
    remove_addr_infos(addr_info_copy, "dead:aaaa::")
    assert addr_info_copy == [ipv4_addr_info]
    remove_addr_infos(addr_info_copy, "107.6.106.83")
    assert addr_info_copy == []


def test_remove_addr_infos_slow_path():
    """Test remove_addr_infos with mis-matched formatting."""
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
    addr_info: List[AddrInfoType] = [ipv6_addr_info, ipv6_addr_info_2, ipv4_addr_info]
    addr_info_copy = addr_info.copy()
    remove_addr_infos(addr_info_copy, "dead:beef:0000:0000:0000:0000:0000:0000")
    assert addr_info_copy == [ipv6_addr_info_2, ipv4_addr_info]
    remove_addr_infos(addr_info_copy, "dead:aaaa:0000:0000:0000:0000:0000:0000")
    assert addr_info_copy == [ipv4_addr_info]
    with pytest.raises(ValueError, match="Address 107.6.106.2 not found in addr_infos"):
        remove_addr_infos(addr_info_copy, "107.6.106.2")
    assert addr_info_copy == [ipv4_addr_info]
