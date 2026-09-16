import pytest
from argos.domain.safe_fetch import FetchPolicyError
import argos.infrastructure.scrapers.limited_http as module

@pytest.fixture
def transport(monkeypatch):
    class Sock:
        def settimeout(self,value): pass
        def close(self): pass
        def shutdown(self,value): pass
    class Pinned:
        socket=Sock()
        def __init__(self,url,address,**kwargs): assert address=='8.8.8.8'
        def __enter__(self): return self
        def __exit__(self,*args): pass
    class Response:
        status=200
        headers={'Content-Type':'text/html'}
        body=b'<html>ok</html>'
        def getheader(self,key,default=None): return self.headers.get(key,default)
        def getheaders(self): return list(self.headers.items())
        def begin(self): pass
        def close(self): pass
        def read(self,size):
            value=self.body[:size];self.body=self.body[size:];return value
    response=Response()
    class Connection:
        def __init__(self,host): assert host=='www.mercadolivre.com.br'
        def request(self,method,path,headers):
            assert method=='GET' and headers['Accept-Encoding']=='identity'
            assert headers['Host']=='www.mercadolivre.com.br'
        def getresponse(self): return response
        def close(self): pass
    monkeypatch.setattr(module,'PinnedTLSConnection',Pinned)
    monkeypatch.setattr(module.http.client,'HTTPConnection',Connection)
    monkeypatch.setattr(module.http.client,'HTTPResponse',lambda sock:response)
    return response

class Resolver:
    def resolve(self,*args,**kwargs): return ['8.8.8.8']

def fetch(): return module.fetch_html_once('https://www.mercadolivre.com.br/p/MLB123',resolver=Resolver())

def test_html_success(transport):
    result = fetch()
    assert result.html == b'<html>ok</html>'
    assert result.final_url == 'https://www.mercadolivre.com.br/p/MLB123'
    assert repr(result) == 'FetchedHTML()'


def test_propagates_declared_charset(transport):
    transport.headers['Content-Type'] = 'text/html; charset="UTF-8"'
    assert fetch().charset == 'UTF-8'


@pytest.mark.parametrize('status,headers,code',[
 (302,{},'redirect_rejected'),(403,{},'http_failed'),
 (200,{'Content-Type':'application/json'},'invalid_content_type'),
 (200,{'Content-Type':'text/html','Content-Encoding':'gzip'},'unsupported_encoding'),
 (200,{'Content-Type':'text/html','Content-Length':'9999999'},'body_too_large'),
])
def test_invalid_response(transport,status,headers,code):
    transport.status=status;transport.headers=headers
    with pytest.raises(FetchPolicyError,match=code): fetch()

def test_stream_without_length_is_bounded(transport,monkeypatch):
    monkeypatch.setattr(module,'MAX_BODY_BYTES',4)
    with pytest.raises(FetchPolicyError,match='body_too_large'): fetch()
