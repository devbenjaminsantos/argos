import pytest
from argos.domain.safe_fetch import FetchPolicyError
from argos.infrastructure.scrapers.resolved_destination import resolve_destination

_URL='https://www.mercadolivre.com.br/p/MLB123'


def test_resolves_original_hostname_once_and_validates_all(monkeypatch):
    monkeypatch.setattr('time.monotonic',lambda:10)
    calls=[]
    class Resolver:
        def resolve(self,hostname,*,timeout):
            calls.append((hostname,timeout))
            return ['8.8.8.8','2606:4700:4700::1111']
    result=resolve_destination(_URL,Resolver(),deadline=12)
    assert calls==[('www.mercadolivre.com.br',2)]
    assert result.addresses==('8.8.8.8','2606:4700:4700::1111')


@pytest.mark.parametrize('addresses',[[],['8.8.8.8','127.0.0.1'],['8.8.8.8']*17])
def test_rejects_entire_invalid_set(monkeypatch,addresses):
    monkeypatch.setattr('time.monotonic',lambda:10)
    class Resolver:
        def resolve(self,*args,**kwargs): return addresses
    with pytest.raises(FetchPolicyError):
        resolve_destination(_URL,Resolver(),deadline=15)


def test_deadline_expired_during_dns_is_rejected(monkeypatch):
    clock=iter([10,16])
    monkeypatch.setattr('time.monotonic',lambda:next(clock))
    class Resolver:
        def resolve(self,*args,**kwargs): return ['8.8.8.8']
    with pytest.raises(FetchPolicyError,match='timeout'):
        resolve_destination(_URL,Resolver(),deadline=15)


def test_invalid_url_never_resolves():
    class Resolver:
        def resolve(self,*args,**kwargs): pytest.fail('DNS must not be called')
    with pytest.raises(FetchPolicyError):
        resolve_destination('https://evil.test/p/MLB123',Resolver(),deadline=100)
