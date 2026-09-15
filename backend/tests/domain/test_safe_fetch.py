import pytest
from argos.domain.safe_fetch import FetchPolicyError, validate_fetch_url, validate_resolved_addresses

@pytest.mark.parametrize('host',['mercadolivre.com.br','www.mercadolivre.com.br','produto.mercadolivre.com.br'])
def test_exact_hosts(host):
    assert validate_fetch_url(f'https://{host}/p/MLB123#tracking')==f'https://{host}/p/MLB123'

@pytest.mark.parametrize('url',[
 'http://www.mercadolivre.com.br/p/MLB123',
 'https://evil.mercadolivre.com.br/p/MLB123',
 'https://mercadolivre.com.br.evil.test/p/MLB123',
 'https://www.mercadolivre.com.br./p/MLB123',
 'https://user:secret@www.mercadolivre.com.br/p/MLB123',
 'https://www.mercadolivre.com.br:444/p/MLB123',
 'https://127.0.0.1/p/MLB123','https://[::1]/p/MLB123',
 'https://www.mercadolivre.com.br/login',
 'https://www.mercadolivre.com.br/p/MLB123\\evil',
])
def test_forbidden_urls(url):
    with pytest.raises(FetchPolicyError) as error:
        validate_fetch_url(url)
    assert url not in str(error.value)

@pytest.mark.parametrize('address',[
 '0.0.0.0','10.0.0.1','100.64.0.1','127.0.0.1','169.254.169.254',
 '172.16.0.1','192.168.1.1','192.0.2.1','198.18.0.1','198.51.100.1',
 '203.0.113.1','224.0.0.1','255.255.255.255','::','::1','fc00::1',
 'fe80::1','ff02::1','2001:db8::1','64:ff9b::a00:1','2002:0808:0808::1',
 '::ffff:127.0.0.1','fe80::1%eth0','2130706433','0177.0.0.1','garbage',
])
def test_entire_mixed_set_is_rejected(address):
    with pytest.raises(FetchPolicyError):
        validate_resolved_addresses(['8.8.8.8',address])

@pytest.mark.parametrize('addresses',[[],['8.8.8.8']*17,None,'8.8.8.8'])
def test_empty_excessive_or_invalid_dns(addresses):
    with pytest.raises(FetchPolicyError):
        validate_resolved_addresses(addresses)


def test_public_addresses_canonicalized_and_deduplicated():
    assert validate_resolved_addresses(['8.8.8.8','2606:4700:4700::1111','::ffff:8.8.8.8'])==('8.8.8.8','2606:4700:4700::1111')
