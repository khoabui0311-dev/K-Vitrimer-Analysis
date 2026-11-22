"""Process-local network guard used only by the packaged offline self-test."""
import socket


def block_external_connections():
    originals = (socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo)

    def check(host):
        if host not in ('127.0.0.1', '::1', 'localhost', b'127.0.0.1', b'::1', b'localhost'):
            raise RuntimeError('Offline self-test blocked a non-loopback network destination.')

    def connect(sock, address):
        if isinstance(address, tuple):
            check(address[0])
        return originals[0](sock, address)

    def connect_ex(sock, address):
        if isinstance(address, tuple):
            check(address[0])
        return originals[1](sock, address)

    def getaddrinfo(host, *args, **kwargs):
        check(host)
        return originals[2](host, *args, **kwargs)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
    socket.getaddrinfo = getaddrinfo

    def restore():
        socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = originals
    return restore
