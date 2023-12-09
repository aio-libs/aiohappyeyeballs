"""Base implementation."""
import asyncio
import collections
import functools
import itertools
import socket
from asyncio import staggered
from typing import Optional


async def create_connection(
    loop: asyncio.AbstractEventLoop,
    addr_infos: list,
    *,
    local_addr_infos: Optional[list] = None,
    happy_eyeballs_delay: Optional[float] = None,
    interleave: Optional[int] = None,
    all_errors: bool = False,
) -> socket.socket:
    """
    Connect to a TCP server.

    Create a streaming transport connection to a given internet host and
    port: socket family AF_INET or socket.AF_INET6 depending on host (or
    family if specified), socket type SOCK_STREAM. protocol_factory must be
    a callable returning a protocol instance.

    This method is a coroutine which will try to establish the connection
    in the background.  When successful, the coroutine returns a
    (transport, protocol) pair.
    """
    if happy_eyeballs_delay is not None and interleave is None:
        # If using happy eyeballs, default to interleave addresses by family
        interleave = 1

    if interleave:
        addr_infos = _interleave_addrinfos(addr_infos, interleave)

    exceptions = []
    if happy_eyeballs_delay is None:
        # not using happy eyeballs
        for addrinfo in addr_infos:
            try:
                sock = await _connect_sock(exceptions, addrinfo, local_addr_infos)
                break
            except OSError:
                continue
    else:  # using happy eyeballs
        sock, _, _ = await staggered.staggered_race(
            (
                functools.partial(_connect_sock, exceptions, addrinfo, local_addr_infos)
                for addrinfo in addr_infos
            ),
            happy_eyeballs_delay,
            loop=loop,
        )

    if sock is None:
        exceptions = [exc for sub in exceptions for exc in sub]
        try:
            if all_errors:
                raise ExceptionGroup("create_connection failed", exceptions)
            if len(exceptions) == 1:
                raise exceptions[0]
            else:
                # If they all have the same str(), raise one.
                model = str(exceptions[0])
                if all(str(exc) == model for exc in exceptions):
                    raise exceptions[0]
                # Raise a combined exception so the user can see all
                # the various error messages.
                raise OSError(
                    "Multiple exceptions: {}".format(
                        ", ".join(str(exc) for exc in exceptions)
                    )
                )
        finally:
            exceptions = None

    return sock


async def _connect_sock(
    loop: asyncio.AbstractEventLoop,
    exceptions: list[BaseException],
    addr_info,
    local_addr_infos=None,
):
    """Create, bind and connect one socket."""
    my_exceptions = []
    exceptions.append(my_exceptions)
    family, type_, proto, _, address = addr_info
    sock = None
    try:
        sock = socket.socket(family=family, type=type_, proto=proto)
        sock.setblocking(False)
        if local_addr_infos is not None:
            for lfamily, _, _, _, laddr in local_addr_infos:
                # skip local addresses of different family
                if lfamily != family:
                    continue
                try:
                    sock.bind(laddr)
                    break
                except OSError as exc:
                    msg = (
                        f"error while attempting to bind on "
                        f"address {laddr!r}: "
                        f"{exc.strerror.lower()}"
                    )
                    exc = OSError(exc.errno, msg)
                    my_exceptions.append(exc)
            else:  # all bind attempts failed
                if my_exceptions:
                    raise my_exceptions.pop()
                else:
                    raise OSError(f"no matching local address with {family=} found")
        await loop.sock_connect(sock, address)
        return sock
    except OSError as exc:
        my_exceptions.append(exc)
        if sock is not None:
            sock.close()
        raise
    except:
        if sock is not None:
            sock.close()
        raise
    finally:
        exceptions = my_exceptions = None


def _interleave_addrinfos(addrinfos, first_address_family_count=1):
    """Interleave list of addrinfo tuples by family."""
    # Group addresses by family
    addrinfos_by_family = collections.OrderedDict()
    for addr in addrinfos:
        family = addr[0]
        if family not in addrinfos_by_family:
            addrinfos_by_family[family] = []
        addrinfos_by_family[family].append(addr)
    addrinfos_lists = list(addrinfos_by_family.values())

    reordered = []
    if first_address_family_count > 1:
        reordered.extend(addrinfos_lists[0][: first_address_family_count - 1])
        del addrinfos_lists[0][: first_address_family_count - 1]
    reordered.extend(
        a
        for a in itertools.chain.from_iterable(itertools.zip_longest(*addrinfos_lists))
        if a is not None
    )
    return reordered
