from uuid import UUID, uuid4

import pytest

from argos.application.errors import ApplicationError
from argos.application.ports.product_collection import CollectedProduct, ProductCollectionError
from argos.application.ports.product_verification import ProductVerificationTarget
from argos.application.use_cases.verify_product import VerifyProduct

URL = "https://www.mercadolivre.com.br/notebook/p/MLB123456"
PRODUCT_ID = UUID("12345678-1234-5678-1234-567812345678")


class Targets:
    def __init__(self, target=None):
        self.target = target
        self.calls = []
    def find_active(self, **values):
        self.calls.append(values)
        return self.target


class Collector:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []
    def collect(self, url):
        self.calls.append(url)
        if self.error:
            raise self.error
        return self.result


def target(**changes):
    values = dict(product_id=PRODUCT_ID, product_key="MLB123456", url=URL,
                  alias="Notebook", target_price_cents=350_000) | changes
    return ProductVerificationTarget(**values)


def collected(**changes):
    values = dict(store="mercado-livre", external_id="MLB123456", url=URL,
                  title="Notebook atual", price_cents=349_990, source="json-ld") | changes
    return CollectedProduct(**values)


def test_owner_scoped_target_is_collected_once_and_compared():
    targets = Targets(target())
    collector = Collector(collected())
    result = VerifyProduct(targets, collector).execute(
        telegram_user_id=700, product_id=PRODUCT_ID)
    assert targets.calls == [{"telegram_user_id": 700, "product_id": PRODUCT_ID}]
    assert collector.calls == [URL]
    assert result.current_price_cents == 349_990
    assert result.target_price_cents == 350_000
    assert result.target_reached is True
    assert result.source == "json-ld"
    assert "Notebook" not in repr(result)


def test_price_above_target_is_not_reached():
    result = VerifyProduct(Targets(target()), Collector(collected(price_cents=350_001))).execute(
        telegram_user_id=700, product_id=PRODUCT_ID)
    assert result.target_reached is False


def test_missing_or_foreign_product_has_same_failure_and_no_collection():
    collector = Collector()
    with pytest.raises(ApplicationError) as raised:
        VerifyProduct(Targets(None), collector).execute(
            telegram_user_id=700, product_id=PRODUCT_ID)
    assert raised.value.code == "product_not_found"
    assert collector.calls == []


@pytest.mark.parametrize("user,product", [
    (0, PRODUCT_ID), (True, PRODUCT_ID), (700, "bad"),
])
def test_invalid_input_stops_before_repository(user, product):
    targets = Targets(target())
    with pytest.raises(ApplicationError, match="Produto para verificação inválido"):
        VerifyProduct(targets, Collector()).execute(
            telegram_user_id=user, product_id=product)
    assert targets.calls == []


@pytest.mark.parametrize("remote,expected", [
    ("access_blocked", "collection_blocked"),
    ("product_unavailable", "product_unavailable"),
    ("price_not_found", "price_not_found"),
    ("timeout", "collection_timeout"),
    ("forbidden_address", "collection_failed"),
])
def test_collection_failures_are_safely_mapped(remote, expected):
    with pytest.raises(ApplicationError) as raised:
        VerifyProduct(Targets(target()), Collector(error=ProductCollectionError(remote))).execute(
            telegram_user_id=700, product_id=PRODUCT_ID)
    assert raised.value.code == expected
    assert URL not in str(raised.value)


def test_redirect_to_different_product_identity_is_rejected():
    with pytest.raises(ApplicationError) as raised:
        VerifyProduct(Targets(target()), Collector(collected(external_id="MLB999"))).execute(
            telegram_user_id=700, product_id=PRODUCT_ID)
    assert raised.value.code == "product_identity_changed"


@pytest.mark.parametrize("changes", [
    {"product_id": "bad"}, {"product_key": "MLB999"}, {"url": "https://evil.test/MLB-123"},
    {"alias": " alias "}, {"target_price_cents": 0}, {"target_price_cents": True},
])
def test_target_contract_rejects_invalid_repository_data(changes):
    with pytest.raises(ValueError, match="Alvo de verificação inválido"):
        target(**changes)
