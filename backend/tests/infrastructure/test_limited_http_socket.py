"""Parse HTTP real via socketpair; TLS permanece falso neste teste."""
import socket
import threading
import pytest
from argos.domain.safe_fetch import FetchPolicyError
import argos.infrastructure.scrapers.limited_http as module

class Resolver:
    def resolve(self,*args,**kwargs): return ['8.8.8.8']

@pytest.mark.parametrize('response,expected',[
 (b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: 2\r\n\r\nok',b'ok'),
 (b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: 0\r\n\r\n',b''),
 (b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n<html>ok</html>',b'<html>ok</html>'),
 (b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nTransfer-Encoding: chunked\r\n\r\n2\r\nok\r\n0\r\n\r\n',b'ok'),
])
def test_real_http_stream_survives_connection_close(monkeypatch,response,expected):
    client,server=socket.socketpair()
    class Pinned:
        socket=client
        def __init__(self,*args,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): client.close()
    monkeypatch.setattr(module,'PinnedTLSConnection',Pinned)
    def serve():
        try:
            server.recv(4096)
            server.sendall(response)
        finally:
            server.close()
    thread=threading.Thread(target=serve)
    thread.start()
    try:
        assert module.fetch_html_once('https://www.mercadolivre.com.br/p/MLB123',resolver=Resolver())==expected
    finally:
        client.close();thread.join(timeout=2)
    assert not thread.is_alive()


def test_real_stream_exceeding_limit_is_rejected(monkeypatch):
    client,server=socket.socketpair()
    class Pinned:
        socket=client
        def __init__(self,*args,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): client.close()
    monkeypatch.setattr(module,'PinnedTLSConnection',Pinned)
    monkeypatch.setattr(module,'MAX_BODY_BYTES',4)
    def serve():
        try:
            server.recv(4096)
            server.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\ntoo large')
        finally: server.close()
    thread=threading.Thread(target=serve);thread.start()
    try:
        with pytest.raises(FetchPolicyError,match='body_too_large'):
            module.fetch_html_once('https://www.mercadolivre.com.br/p/MLB123',resolver=Resolver())
    finally:
        client.close();thread.join(timeout=2)


def test_total_deadline_interrupts_blocked_read(monkeypatch):
    client,server=socket.socketpair()
    stopped=threading.Event()
    class Pinned:
        socket=client
        def __init__(self,*args,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): client.close()
    monkeypatch.setattr(module,'PinnedTLSConnection',Pinned)
    monkeypatch.setattr(module,'TOTAL_TIMEOUT_SECONDS',0.3)
    def serve():
        try:
            server.recv(4096)
            server.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: 100\r\n\r\nx')
            stopped.wait(3)
        finally: server.close()
    thread=threading.Thread(target=serve);thread.start()
    try:
        with pytest.raises(FetchPolicyError,match='timeout'):
            module.fetch_html_once('https://www.mercadolivre.com.br/p/MLB123',resolver=Resolver())
    finally:
        stopped.set();client.close();thread.join(timeout=2)
    assert not thread.is_alive()


@pytest.mark.parametrize('headers,body', [
    (b'Content-Length: 10\r\n', b'short'),
    (b'Content-Length: 0\r\nContent-Length: 10\r\n', b''),
    (b'Content-Length: 2\r\nContent-Length: 2\r\n', b'ok'),
    (b'Content-Length: 2, 2\r\n', b'ok'),
    (b'Content-Length: +2\r\n', b'ok'),
    (b'Content-Length: -1\r\n', b'ok'),
    (b'Content-Length: nope\r\n', b'ok'),
    (b'Transfer-Encoding: gzip\r\n', b'ok'),
    (b'Transfer-Encoding: gzip, chunked\r\n', b'2\r\nok\r\n0\r\n\r\n'),
    (b'Transfer-Encoding: chunked\r\nTransfer-Encoding: chunked\r\n', b''),
    (b'Transfer-Encoding: chunked\r\nContent-Length: 2\r\n', b'2\r\nok\r\n0\r\n\r\n'),
    (b'Transfer-Encoding: chunked\r\n', b'5\r\nok'),
    (b'Transfer-Encoding: chunked\r\n', b'2\r\nok\r\n'),
])
def test_real_http_rejects_truncated_or_ambiguous_framing(monkeypatch, headers, body):
    client, server = socket.socketpair()
    class Pinned:
        socket = client
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): client.close()
    monkeypatch.setattr(module, 'PinnedTLSConnection', Pinned)
    def serve():
        try:
            server.recv(4096)
            server.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n' + headers + b'\r\n' + body)
        finally:
            server.close()
    thread = threading.Thread(target=serve)
    thread.start()
    try:
        with pytest.raises(FetchPolicyError, match='http_failed'):
            module.fetch_html_once('https://www.mercadolivre.com.br/p/MLB123', resolver=Resolver())
    finally:
        client.close()
        thread.join(timeout=2)
    assert not thread.is_alive()
