"""Redirecionamentos com DNS e transporte falsos, sem Internet."""
import pytest
from argos.domain.safe_fetch import FetchPolicyError
import argos.infrastructure.scrapers.limited_http as module
from test_limited_http import transport, Resolver

BASE = 'https://www.mercadolivre.com.br/p/MLB123'

@pytest.mark.parametrize('status', [301, 302, 303, 307, 308])
def test_relative_redirect_is_followed(transport, status):
    transport.status = status
    transport.headers['Location'] = '/p/MLB456'
    original_begin = transport.begin
    calls = []
    def begin():
        calls.append(True)
        if len(calls) == 2:
            transport.status = 200
        original_begin()
    transport.begin = begin
    result = module.fetch_html_once(BASE, resolver=Resolver())
    assert result.html == b'<html>ok</html>'
    assert result.final_url == 'https://www.mercadolivre.com.br/p/MLB456'
    assert len(calls) == 2

@pytest.mark.parametrize('location', ['', 'http://www.mercadolivre.com.br/p/MLB456',
    'https://evil.example/p/MLB456', 'https://u:p@www.mercadolivre.com.br/p/MLB456',
    'https://www.mercadolivre.com.br:8443/p/MLB456', '//127.0.0.1/p/MLB456',
    '/p/MLB456\r\nInjected: yes', 'x' * 2049, BASE + '#fragment'])
def test_invalid_target_or_cycle_is_rejected(transport, location):
    transport.status = 302
    transport.headers['Location'] = location
    class CountingResolver(Resolver):
        calls = 0
        def resolve(self, *args, **kwargs):
            self.calls += 1
            return super().resolve(*args, **kwargs)
    resolver = CountingResolver()
    with pytest.raises(FetchPolicyError, match='redirect_rejected'):
        module.fetch_html_once(BASE, resolver=resolver)
    assert resolver.calls == 1

def test_rebinding_is_rejected_before_second_transport(transport):
    transport.status = 302
    transport.headers['Location'] = '/p/MLB456'
    class RebindingResolver:
        calls = 0
        def resolve(self, *args, **kwargs):
            self.calls += 1
            return ['8.8.8.8'] if self.calls == 1 else ['8.8.8.8', '127.0.0.1']
    resolver = RebindingResolver()
    with pytest.raises(FetchPolicyError, match='forbidden_address'):
        module.fetch_html_once(BASE, resolver=resolver)
    assert resolver.calls == 2

def test_redirect_limit_and_shared_deadline(monkeypatch):
    calls = []
    def hop(url, *, resolver, deadline):
        calls.append((url, deadline))
        return module._Redirect(f'https://www.mercadolivre.com.br/p/MLB{456 + len(calls)}')
    monkeypatch.setattr(module, '_fetch_hop', hop)
    with pytest.raises(FetchPolicyError, match='redirect_limit'):
        module.fetch_html_once(BASE, resolver=Resolver())
    assert len(calls) == 4
    assert len({deadline for url, deadline in calls}) == 1

def test_cross_host_uses_new_ip_and_host_header(transport, monkeypatch):
    target = 'https://produto.mercadolivre.com.br/MLB-456-produto'
    transport.status = 302
    transport.headers['Location'] = target
    opened, closed, headers = [], [], []
    original_pinned = module.PinnedTLSConnection
    class Pinned(original_pinned):
        def __init__(self, url, address, **kwargs): opened.append((url, address))
        def __exit__(self, *args): closed.append(True)
    class Connection:
        def __init__(self, host): pass
        def request(self, method, path, headers):
            assert method == 'GET'
            assert headers['Accept-Encoding'] == 'identity'
            captured.append(headers['Host'])
        def close(self): pass
    captured = headers
    begins = []
    def begin():
        begins.append(True)
        if len(begins) == 2: transport.status = 200
    transport.begin = begin
    class ChangingResolver:
        def resolve(self, host, **kwargs):
            if host == 'produto.mercadolivre.com.br':
                assert len(closed) == 1
                return ['1.1.1.1']
            return ['8.8.8.8']
    monkeypatch.setattr(module, 'PinnedTLSConnection', Pinned)
    monkeypatch.setattr(module.http.client, 'HTTPConnection', Connection)
    result = module.fetch_html_once(BASE, resolver=ChangingResolver())
    assert result.html == b'<html>ok</html>'
    assert result.final_url == target
    assert opened == [(BASE, '8.8.8.8'), (target, '1.1.1.1')]
    assert headers == ['www.mercadolivre.com.br', 'produto.mercadolivre.com.br']
    assert len(closed) == 2


def test_expired_deadline_prevents_next_dns(transport, monkeypatch):
    transport.status = 302
    transport.headers['Location'] = '/p/MLB456'
    clock = [100.0]
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock[0])
    def close(): clock[0] += module.TOTAL_TIMEOUT_SECONDS + 1
    transport.close = close
    class CountingResolver(Resolver):
        calls = 0
        def resolve(self, *args, **kwargs):
            self.calls += 1
            return super().resolve(*args, **kwargs)
    resolver = CountingResolver()
    with pytest.raises(FetchPolicyError, match='timeout'):
        module.fetch_html_once(BASE, resolver=resolver)
    assert resolver.calls == 1
