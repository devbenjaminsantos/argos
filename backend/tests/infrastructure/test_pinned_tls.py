import socket
import pytest
from argos.infrastructure.scrapers.pinned_tls import PinnedTLSConnection

@pytest.mark.parametrize('address,family',[('8.8.8.8',socket.AF_INET),('2606:4700:4700::1111',socket.AF_INET6)])
def test_direct_ip_socket_and_original_tls_hostname(monkeypatch,address,family):
    calls=[]
    class Raw:
        def settimeout(self,value): calls.append(('timeout',value))
        def connect(self,value): calls.append(('connect',value))
        def close(self): calls.append(('close',))
    raw=Raw()
    def new_socket(actual_family,kind):
        assert actual_family==family and kind==socket.SOCK_STREAM
        return raw
    class Context:
        def wrap_socket(self,actual,server_hostname):
            assert actual is raw and server_hostname=='www.mercadolivre.com.br'
            return raw
    monkeypatch.setattr('socket.socket',new_socket)
    monkeypatch.setattr('socket.getaddrinfo',lambda *args:pytest.fail('DNS must not be resolved'))
    monkeypatch.setattr('ssl.create_default_context',lambda:Context())
    with PinnedTLSConnection('https://www.mercadolivre.com.br/p/MLB123',address):
        assert ('connect',(address,443)) in calls
    assert calls[-1]==('close',)


def test_failure_closes_socket_and_hides_details(monkeypatch):
    class Raw:
        closed=False
        def settimeout(self,value): pass
        def connect(self,value): raise OSError('sensitive details')
        def close(self): self.closed=True
    raw=Raw()
    monkeypatch.setattr('socket.socket',lambda *args:raw)
    with pytest.raises(RuntimeError,match='^transport_failed$'):
        PinnedTLSConnection('https://www.mercadolivre.com.br/p/MLB123','8.8.8.8').connect()
    assert raw.closed


@pytest.mark.parametrize('address',['127.0.0.1','169.254.169.254','::ffff:10.0.0.1'])
def test_forbidden_ip_never_opens_socket(monkeypatch,address):
    monkeypatch.setattr('socket.socket',lambda *args:pytest.fail('No connection allowed'))
    with pytest.raises(ValueError):
        PinnedTLSConnection('https://www.mercadolivre.com.br/p/MLB123',address)
