import pytest

from argos.domain.mercado_livre_url import normalize_mercado_livre_product_url


@pytest.mark.parametrize("url", [
    "https://mercadolivre.com.br/p/MLB123",
    "https://www.mercadolivre.com.br/caneca-personalizada-hello-kitty/up/MLBU1977786059",
    "https://www.mercadolivre.com.br/up/MLBU1977786059",
    "https://www.mercadolivre.com.br/produto/p/MLB123",
    "https://produto.mercadolivre.com.br/MLB-123-produto-_JM",
])
def test_accepts_product_and_catalog_paths(url):
    assert normalize_mercado_livre_product_url(url) == url


@pytest.mark.parametrize("url", [
    "http://produto.mercadolivre.com.br/MLB-123",
    "https://mercadolivre.com.br.evil.test/MLB-123",
    "https://evilmercadolivre.com.br/MLB-123",
    "https://user:password@mercadolivre.com.br/MLB-123",
    "https://mercadolivre.com.br:444/MLB-123",
    "https://mercadolivre.com.br:/MLB-123",
    "https://mercadolivre.com.br./MLB-123",
    "https://mercadolivre.com.br/search/MLB-123",
    "https://mercadolivre.com.br/up/MLBUabc",
    "https://mercadolivre.com.br/up/MLBU123/redirect",
    "https://mercadolivre.com.br/up/MLB123",
    "https://evil.test/item/up/MLBU123",
    "https://mercadolivre.com.br/MLB-123/redirect",
    "https://mercadolivre.com.br/%4dLB-123",
    "https://mercadolivre.com.br/MLB-123\nattack",
    "https://mercadolivre.com.br\\@evil.test/MLB-123",
    "https://meli.la/abc", "https://127.0.0.1/MLB-123",
    "https://mercadolivre.com.br/", "x" * 2049,
])
def test_rejects_ambiguous_non_product_and_external_urls(url):
    with pytest.raises(ValueError, match="URL de produto inválida"):
        normalize_mercado_livre_product_url(url)


def test_removes_tracking_and_fragment_preserving_functional_parameters():
    assert normalize_mercado_livre_product_url(
        "https://mercadolivre.com.br/p/MLB123?UTM_source=x&gclid=y&variation=7&variation=8&empty=#details"
    ) == "https://mercadolivre.com.br/p/MLB123?variation=7&variation=8&empty="


def test_user_product_url_removes_recommendation_fragment():
    base = "https://www.mercadolivre.com.br/caneca-personalizada-hello-kitty/up/MLBU1977786059"
    assert normalize_mercado_livre_product_url(base + "#reco_item_pos=0&reco_backend=item_decorator&c_id=/home/navigation") == base
