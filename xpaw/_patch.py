# coding=utf-8

import socket
import struct

_socket_init = socket.socket.__init__


def socket_init(*args, **kw):
    _socket_init(*args, **kw)
    args[0].setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))


socket.socket.__init__ = socket_init
