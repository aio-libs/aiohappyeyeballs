"""Utility functions for aiohappyeyeballs."""

import ipaddress
from typing import Dict, List

from .types import AddrInfoType


def pop_addr_infos_interleave(addr_infos: List[AddrInfoType], interleave: int) -> None:
    """
    Pop addr_info from the list of addr_infos by family up to interleave times.

    The interleave parameter is used to know how many addr_infos for
    each family should be popped of the top of the list.
    """
    seen: Dict[int, int] = {}
    to_remove: List[AddrInfoType] = []
    for addr_info in addr_infos:
        family = addr_info[0]
        if family not in seen:
            seen[family] = 0
        if seen[family] < interleave:
            to_remove.append(addr_info)
        seen[family] += 1
    for addr_info in to_remove:
        addr_infos.remove(addr_info)


def remove_addr_infos(
    addr_infos: List[AddrInfoType],
    addr: str,
) -> None:
    """Pop addr_info from the list of addr_infos by addr."""
    bad_addrs_infos: List[AddrInfoType] = []
    for addr_info in addr_infos:
        if addr_info[-1][0] == addr:
            bad_addrs_infos.append(addr_info)
    if bad_addrs_infos:
        for bad_addr_info in bad_addrs_infos:
            addr_infos.remove(bad_addr_info)
        return
    # Slow path in case addr is formatted differently
    ip_address = ipaddress.ip_address(addr)
    for addr_info in addr_infos:
        if ip_address == ipaddress.ip_address(addr_info[-1][0]):
            bad_addrs_infos.append(addr_info)
    if bad_addrs_infos:
        for bad_addr_info in bad_addrs_infos:
            addr_infos.remove(bad_addr_info)
        return
    raise ValueError(f"Address {addr} not found in addr_infos")
