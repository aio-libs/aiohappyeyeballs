API Reference
=============

.. autodata:: aiohappyeyeballs.AddrInfoType

   A tuple representing socket address information.

   Indexes:

   **[0]** ``Union[int, socket.AddressFamily]``

      The address family, e.g. ``socket.AF_INET``

   **[1]** ``Union[int, socket.SocketKind]``

      The type of socket, e.g. ``socket.SOCK_STREAM``.

   **[2]** ``int``

      The protocol number, e.g. ``socket.IPPROTO_TCP``.

   **[3]** ``str``

      The canonical name of the address, e.g. ``"www.example.com"``.

   **[4]** ``Tuple``

      The socket address tuple, e.g. ``("127.0.0.1", 443)``.

.. autodata:: aiohappyeyeballs.SocketFactoryType

   A callable that creates a socket from an ``AddrInfoType``.


   :param AddrInfoType: Address info for creating the socket containing
      the address family, socket type, protocol, host address, and
      additional details.

   :rtype: ``socket.socket``


.. automodule:: aiohappyeyeballs
   :members:
   :undoc-members:
   :show-inheritance:
