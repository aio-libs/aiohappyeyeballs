"""Tests for base_events.py"""

import asyncio
import socket
import sys
import unittest
from test.support import socket_helper
from test.test_asyncio import utils as test_utils
from unittest import mock

MOCK_ANY = mock.ANY


def tearDownModule():
    asyncio.set_event_loop_policy(None)


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
    return mock.patch("asyncio.base_events.socket", new_callable=mock_socket_module)(f)


class MyProto(asyncio.Protocol):
    done = None

    def __init__(self, create_future=False):
        self.state = "INITIAL"
        self.nbytes = 0
        if create_future:
            self.done = asyncio.get_running_loop().create_future()

    def _assert_state(self, *expected):
        if self.state not in expected:
            raise AssertionError(f"state: {self.state!r}, expected: {expected!r}")

    def connection_made(self, transport):
        self.transport = transport
        self._assert_state("INITIAL")
        self.state = "CONNECTED"
        transport.write(b"GET / HTTP/1.0\r\nHost: example.com\r\n\r\n")

    def data_received(self, data):
        self._assert_state("CONNECTED")
        self.nbytes += len(data)

    def eof_received(self):
        self._assert_state("CONNECTED")
        self.state = "EOF"

    def connection_lost(self, exc):
        self._assert_state("CONNECTED", "EOF")
        self.state = "CLOSED"
        if self.done:
            self.done.set_result(None)


class BaseEventLoopWithSelectorTests(test_utils.TestCase):
    def setUp(self):
        super().setUp()
        self.loop = asyncio.SelectorEventLoop()
        self.set_event_loop(self.loop)

    @mock.patch("socket.getnameinfo")
    def test_getnameinfo(self, m_gai):
        m_gai.side_effect = lambda *args: 42
        r = self.loop.run_until_complete(self.loop.getnameinfo(("abc", 123)))
        self.assertEqual(r, 42)

    @patch_socket
    def test_create_connection_multiple_errors(self, m_socket):
        class MyProto(asyncio.Protocol):
            pass

        async def getaddrinfo(*args, **kw):
            return [
                (2, 1, 6, "", ("107.6.106.82", 80)),
                (2, 1, 6, "", ("107.6.106.82", 80)),
            ]

        def getaddrinfo_task(*args, **kwds):
            return self.loop.create_task(getaddrinfo(*args, **kwds))

        idx = -1
        errors = ["err1", "err2"]

        def _socket(*args, **kw):
            nonlocal idx, errors
            idx += 1
            raise OSError(errors[idx])

        m_socket.socket = _socket

        self.loop.getaddrinfo = getaddrinfo_task

        coro = self.loop.create_connection(MyProto, "example.com", 80)
        with self.assertRaises(OSError) as cm:
            self.loop.run_until_complete(coro)

        self.assertEqual(str(cm.exception), "Multiple exceptions: err1, err2")

        idx = -1
        coro = self.loop.create_connection(MyProto, "example.com", 80, all_errors=True)
        with self.assertRaises(ExceptionGroup) as cm:
            self.loop.run_until_complete(coro)

        self.assertIsInstance(cm.exception, ExceptionGroup)
        for e in cm.exception.exceptions:
            self.assertIsInstance(e, OSError)

    @patch_socket
    def test_create_connection_timeout(self, m_socket):
        # Ensure that the socket is closed on timeout
        sock = mock.Mock()
        m_socket.socket.return_value = sock

        def getaddrinfo(*args, **kw):
            fut = self.loop.create_future()
            addr = (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 80))
            fut.set_result([addr])
            return fut

        self.loop.getaddrinfo = getaddrinfo

        with mock.patch.object(
            self.loop, "sock_connect", side_effect=asyncio.TimeoutError
        ):
            coro = self.loop.create_connection(MyProto, "127.0.0.1", 80)
            with self.assertRaises(asyncio.TimeoutError):
                self.loop.run_until_complete(coro)
            self.assertTrue(sock.close.called)

    def test_create_connection_host_port_sock(self):
        coro = self.loop.create_connection(MyProto, "example.com", 80, sock=object())
        self.assertRaises(ValueError, self.loop.run_until_complete, coro)

    def test_create_connection_wrong_sock(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        with sock:
            coro = self.loop.create_connection(MyProto, sock=sock)
            with self.assertRaisesRegex(ValueError, "A Stream Socket was expected"):
                self.loop.run_until_complete(coro)

    def test_create_connection_no_host_port_sock(self):
        coro = self.loop.create_connection(MyProto)
        self.assertRaises(ValueError, self.loop.run_until_complete, coro)

    def test_create_connection_no_getaddrinfo(self):
        async def getaddrinfo(*args, **kw):
            return []

        def getaddrinfo_task(*args, **kwds):
            return self.loop.create_task(getaddrinfo(*args, **kwds))

        self.loop.getaddrinfo = getaddrinfo_task
        coro = self.loop.create_connection(MyProto, "example.com", 80)
        self.assertRaises(OSError, self.loop.run_until_complete, coro)

    def test_create_connection_connect_err(self):
        async def getaddrinfo(*args, **kw):
            return [(2, 1, 6, "", ("107.6.106.82", 80))]

        def getaddrinfo_task(*args, **kwds):
            return self.loop.create_task(getaddrinfo(*args, **kwds))

        self.loop.getaddrinfo = getaddrinfo_task
        self.loop.sock_connect = mock.Mock()
        self.loop.sock_connect.side_effect = OSError

        coro = self.loop.create_connection(MyProto, "example.com", 80)
        self.assertRaises(OSError, self.loop.run_until_complete, coro)

        coro = self.loop.create_connection(MyProto, "example.com", 80, all_errors=True)
        with self.assertRaises(ExceptionGroup) as cm:
            self.loop.run_until_complete(coro)

        self.assertIsInstance(cm.exception, ExceptionGroup)
        self.assertEqual(len(cm.exception.exceptions), 1)
        self.assertIsInstance(cm.exception.exceptions[0], OSError)

    def test_create_connection_multiple(self):
        async def getaddrinfo(*args, **kw):
            return [(2, 1, 6, "", ("0.0.0.1", 80)), (2, 1, 6, "", ("0.0.0.2", 80))]

        def getaddrinfo_task(*args, **kwds):
            return self.loop.create_task(getaddrinfo(*args, **kwds))

        self.loop.getaddrinfo = getaddrinfo_task
        self.loop.sock_connect = mock.Mock()
        self.loop.sock_connect.side_effect = OSError

        coro = self.loop.create_connection(
            MyProto, "example.com", 80, family=socket.AF_INET
        )
        with self.assertRaises(OSError):
            self.loop.run_until_complete(coro)

        coro = self.loop.create_connection(
            MyProto, "example.com", 80, family=socket.AF_INET, all_errors=True
        )
        with self.assertRaises(ExceptionGroup) as cm:
            self.loop.run_until_complete(coro)

        self.assertIsInstance(cm.exception, ExceptionGroup)
        for e in cm.exception.exceptions:
            self.assertIsInstance(e, OSError)

    @patch_socket
    def test_create_connection_multiple_errors_local_addr(self, m_socket):
        def bind(addr):
            if addr[0] == "0.0.0.1":
                err = OSError("Err")
                err.strerror = "Err"
                raise err

        m_socket.socket.return_value.bind = bind

        async def getaddrinfo(*args, **kw):
            return [(2, 1, 6, "", ("0.0.0.1", 80)), (2, 1, 6, "", ("0.0.0.2", 80))]

        def getaddrinfo_task(*args, **kwds):
            return self.loop.create_task(getaddrinfo(*args, **kwds))

        self.loop.getaddrinfo = getaddrinfo_task
        self.loop.sock_connect = mock.Mock()
        self.loop.sock_connect.side_effect = OSError("Err2")

        coro = self.loop.create_connection(
            MyProto, "example.com", 80, family=socket.AF_INET, local_addr=(None, 8080)
        )
        with self.assertRaises(OSError) as cm:
            self.loop.run_until_complete(coro)

        self.assertTrue(str(cm.exception).startswith("Multiple exceptions: "))
        self.assertTrue(m_socket.socket.return_value.close.called)

        coro = self.loop.create_connection(
            MyProto,
            "example.com",
            80,
            family=socket.AF_INET,
            local_addr=(None, 8080),
            all_errors=True,
        )
        with self.assertRaises(ExceptionGroup) as cm:
            self.loop.run_until_complete(coro)

        self.assertIsInstance(cm.exception, ExceptionGroup)
        for e in cm.exception.exceptions:
            self.assertIsInstance(e, OSError)

    def _test_create_connection_ip_addr(self, m_socket, allow_inet_pton):
        # Test the fallback code, even if this system has inet_pton.
        if not allow_inet_pton:
            del m_socket.inet_pton

        m_socket.getaddrinfo = socket.getaddrinfo
        sock = m_socket.socket.return_value

        self.loop._add_reader = mock.Mock()
        self.loop._add_writer = mock.Mock()

        coro = self.loop.create_connection(asyncio.Protocol, "1.2.3.4", 80)
        t, p = self.loop.run_until_complete(coro)
        try:
            sock.connect.assert_called_with(("1.2.3.4", 80))
            _, kwargs = m_socket.socket.call_args
            self.assertEqual(kwargs["family"], m_socket.AF_INET)
            self.assertEqual(kwargs["type"], m_socket.SOCK_STREAM)
        finally:
            t.close()
            test_utils.run_briefly(self.loop)  # allow transport to close

        if socket_helper.IPV6_ENABLED:
            sock.family = socket.AF_INET6
            coro = self.loop.create_connection(asyncio.Protocol, "::1", 80)
            t, p = self.loop.run_until_complete(coro)
            try:
                # Without inet_pton we use getaddrinfo, which transforms
                # ('::1', 80) to ('::1', 80, 0, 0). The last 0s are flow info,
                # scope id.
                [address] = sock.connect.call_args[0]
                host, port = address[:2]
                self.assertRegex(host, r"::(0\.)*1")
                self.assertEqual(port, 80)
                _, kwargs = m_socket.socket.call_args
                self.assertEqual(kwargs["family"], m_socket.AF_INET6)
                self.assertEqual(kwargs["type"], m_socket.SOCK_STREAM)
            finally:
                t.close()
                test_utils.run_briefly(self.loop)  # allow transport to close

    @unittest.skipUnless(socket_helper.IPV6_ENABLED, "no IPv6 support")
    @unittest.skipIf(
        sys.platform.startswith("aix"),
        "bpo-25545: IPv6 scope id and getaddrinfo() behave differently on AIX",
    )
    @patch_socket
    def test_create_connection_ipv6_scope(self, m_socket):
        m_socket.getaddrinfo = socket.getaddrinfo
        sock = m_socket.socket.return_value
        sock.family = socket.AF_INET6

        self.loop._add_reader = mock.Mock()
        self.loop._add_writer = mock.Mock()

        coro = self.loop.create_connection(asyncio.Protocol, "fe80::1%1", 80)
        t, p = self.loop.run_until_complete(coro)
        try:
            sock.connect.assert_called_with(("fe80::1", 80, 0, 1))
            _, kwargs = m_socket.socket.call_args
            self.assertEqual(kwargs["family"], m_socket.AF_INET6)
            self.assertEqual(kwargs["type"], m_socket.SOCK_STREAM)
        finally:
            t.close()
            test_utils.run_briefly(self.loop)  # allow transport to close

    @patch_socket
    def test_create_connection_ip_addr(self, m_socket):
        self._test_create_connection_ip_addr(m_socket, True)

    @patch_socket
    def test_create_connection_no_inet_pton(self, m_socket):
        self._test_create_connection_ip_addr(m_socket, False)

    @patch_socket
    def test_create_connection_service_name(self, m_socket):
        m_socket.getaddrinfo = socket.getaddrinfo
        sock = m_socket.socket.return_value

        self.loop._add_reader = mock.Mock()
        self.loop._add_writer = mock.Mock()

        for service, port in ("http", 80), (b"http", 80):
            coro = self.loop.create_connection(asyncio.Protocol, "127.0.0.1", service)

            t, p = self.loop.run_until_complete(coro)
            try:
                sock.connect.assert_called_with(("127.0.0.1", port))
                _, kwargs = m_socket.socket.call_args
                self.assertEqual(kwargs["family"], m_socket.AF_INET)
                self.assertEqual(kwargs["type"], m_socket.SOCK_STREAM)
            finally:
                t.close()
                test_utils.run_briefly(self.loop)  # allow transport to close

        for service in "nonsense", b"nonsense":
            coro = self.loop.create_connection(asyncio.Protocol, "127.0.0.1", service)

            with self.assertRaises(OSError):
                self.loop.run_until_complete(coro)

    def test_create_connection_no_local_addr(self):
        async def getaddrinfo(host, *args, **kw):
            if host == "example.com":
                return [
                    (2, 1, 6, "", ("107.6.106.82", 80)),
                    (2, 1, 6, "", ("107.6.106.82", 80)),
                ]
            else:
                return []

        def getaddrinfo_task(*args, **kwds):
            return self.loop.create_task(getaddrinfo(*args, **kwds))

        self.loop.getaddrinfo = getaddrinfo_task

        coro = self.loop.create_connection(
            MyProto, "example.com", 80, family=socket.AF_INET, local_addr=(None, 8080)
        )
        self.assertRaises(OSError, self.loop.run_until_complete, coro)

    @patch_socket
    def test_create_connection_bluetooth(self, m_socket):
        # See http://bugs.python.org/issue27136, fallback to getaddrinfo when
        # we can't recognize an address is resolved, e.g. a Bluetooth address.
        addr = ("00:01:02:03:04:05", 1)

        def getaddrinfo(host, port, *args, **kw):
            self.assertEqual((host, port), addr)
            return [(999, 1, 999, "", (addr, 1))]

        m_socket.getaddrinfo = getaddrinfo
        sock = m_socket.socket()
        coro = self.loop.sock_connect(sock, addr)
        self.loop.run_until_complete(coro)

    def test_create_connection_ssl_server_hostname_default(self):
        self.loop.getaddrinfo = mock.Mock()

        def mock_getaddrinfo(*args, **kwds):
            f = self.loop.create_future()
            f.set_result(
                [
                    (
                        socket.AF_INET,
                        socket.SOCK_STREAM,
                        socket.SOL_TCP,
                        "",
                        ("1.2.3.4", 80),
                    )
                ]
            )
            return f

        self.loop.getaddrinfo.side_effect = mock_getaddrinfo
        self.loop.sock_connect = mock.Mock()
        self.loop.sock_connect.return_value = self.loop.create_future()
        self.loop.sock_connect.return_value.set_result(None)
        self.loop._make_ssl_transport = mock.Mock()

        class _SelectorTransportMock:
            _sock = None

            def get_extra_info(self, key):
                return mock.Mock()

            def close(self):
                self._sock.close()

        def mock_make_ssl_transport(sock, protocol, sslcontext, waiter, **kwds):
            waiter.set_result(None)
            transport = _SelectorTransportMock()
            transport._sock = sock
            return transport

        self.loop._make_ssl_transport.side_effect = mock_make_ssl_transport
        ANY = mock.ANY
        handshake_timeout = object()
        shutdown_timeout = object()
        # First try the default server_hostname.
        self.loop._make_ssl_transport.reset_mock()
        coro = self.loop.create_connection(
            MyProto,
            "python.org",
            80,
            ssl=True,
            ssl_handshake_timeout=handshake_timeout,
            ssl_shutdown_timeout=shutdown_timeout,
        )
        transport, _ = self.loop.run_until_complete(coro)
        transport.close()
        self.loop._make_ssl_transport.assert_called_with(
            ANY,
            ANY,
            ANY,
            ANY,
            server_side=False,
            server_hostname="python.org",
            ssl_handshake_timeout=handshake_timeout,
            ssl_shutdown_timeout=shutdown_timeout,
        )
        # Next try an explicit server_hostname.
        self.loop._make_ssl_transport.reset_mock()
        coro = self.loop.create_connection(
            MyProto,
            "python.org",
            80,
            ssl=True,
            server_hostname="perl.com",
            ssl_handshake_timeout=handshake_timeout,
            ssl_shutdown_timeout=shutdown_timeout,
        )
        transport, _ = self.loop.run_until_complete(coro)
        transport.close()
        self.loop._make_ssl_transport.assert_called_with(
            ANY,
            ANY,
            ANY,
            ANY,
            server_side=False,
            server_hostname="perl.com",
            ssl_handshake_timeout=handshake_timeout,
            ssl_shutdown_timeout=shutdown_timeout,
        )
        # Finally try an explicit empty server_hostname.
        self.loop._make_ssl_transport.reset_mock()
        coro = self.loop.create_connection(
            MyProto,
            "python.org",
            80,
            ssl=True,
            server_hostname="",
            ssl_handshake_timeout=handshake_timeout,
            ssl_shutdown_timeout=shutdown_timeout,
        )
        transport, _ = self.loop.run_until_complete(coro)
        transport.close()
        self.loop._make_ssl_transport.assert_called_with(
            ANY,
            ANY,
            ANY,
            ANY,
            server_side=False,
            server_hostname="",
            ssl_handshake_timeout=handshake_timeout,
            ssl_shutdown_timeout=shutdown_timeout,
        )

    def test_create_connection_no_ssl_server_hostname_errors(self):
        # When not using ssl, server_hostname must be None.
        coro = self.loop.create_connection(
            MyProto, "python.org", 80, server_hostname=""
        )
        self.assertRaises(ValueError, self.loop.run_until_complete, coro)
        coro = self.loop.create_connection(
            MyProto, "python.org", 80, server_hostname="python.org"
        )
        self.assertRaises(ValueError, self.loop.run_until_complete, coro)

    def test_create_connection_ssl_server_hostname_errors(self):
        # When using ssl, server_hostname may be None if host is non-empty.
        coro = self.loop.create_connection(MyProto, "", 80, ssl=True)
        self.assertRaises(ValueError, self.loop.run_until_complete, coro)
        coro = self.loop.create_connection(MyProto, None, 80, ssl=True)
        self.assertRaises(ValueError, self.loop.run_until_complete, coro)
        sock = socket.socket()
        coro = self.loop.create_connection(MyProto, None, None, ssl=True, sock=sock)
        self.addCleanup(sock.close)
        self.assertRaises(ValueError, self.loop.run_until_complete, coro)

    def test_create_connection_ssl_timeout_for_plain_socket(self):
        coro = self.loop.create_connection(
            MyProto, "example.com", 80, ssl_handshake_timeout=1
        )
        with self.assertRaisesRegex(
            ValueError, "ssl_handshake_timeout is only meaningful with ssl"
        ):
            self.loop.run_until_complete(coro)


if __name__ == "__main__":
    unittest.main()
