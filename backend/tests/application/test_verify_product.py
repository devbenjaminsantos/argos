from datetime import datetime, timezone
from uuid import UUID

import pytest

from argos.application.errors import ApplicationError
from argos.application.ports.product_collection import CollectedProduct, ProductCollectionError
from argos.application.ports.product_verification import ProductVerificationTarget
from argos.application.use_cases.verify_product import VerifyProduct

URL = "https://www.mercadolivre.com.br/notebook/p/MLB123456"
PRODUCT_ID = UUID("12345678-1234-5678-1234-567812345678")
OBSERVATION_ID = UUID("a3000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 9, 16, 18, 0, tzinfo=timezone.utc)


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


class Observations:
    def __init__(self, error=None):
        self.items = []
        self.error = error

    def append(self, item):
        if self.error:
            raise self.error
        self.items.append(item)


def target(**changes):
    values = dict(product_id=PRODUCT_ID, product_key="MLB123456", url=URL,
                  alias="Notebook", target_price_cents=350_000) | changes
    return ProductVerificationTarget(**values)


def collected(**changes):
    values = dict(store="mercado-livre", external_id="MLB123456", url=URL,
                  title="Notebook atual", price_cents=349_990,
                  source="json-ld") | changes
    return CollectedProduct(**values)


def execute(targets, collector, observations, **changes):
    values = dict(telegram_user_id=700, product_id=PRODUCT_ID,
                  observation_id=OBSERVATION_ID, observed_at=NOW) | changes
    return VerifyProduct(targets, collector, observations).execute(**values)


def test_owner_scoped_target_is_collected_once_persisted_and_compared():
    targets = Targets(target())
    collector = Collector(collected())
    observations = Observations()
    result = execute(targets, collector, observations)
    assert targets.calls == [{"telegram_user_id": 700, "product_id": PRODUCT_ID}]
    assert collector.calls == [URL]
    assert result.current_price_cents == 349_990
    assert result.target_price_cents == 350_000
    assert result.target_reached is True
    assert result.source == "json-ld"
    assert "Notebook" not in repr(result)
    saved = observations.items[0]
    assert saved.observation_id == OBSERVATION_ID
    assert saved.product_id == PRODUCT_ID
    assert saved.telegram_user_id == 700
    assert saved.observed_at == NOW
    assert saved.target_price_cents == 350_000
    assert saved.status == "success"
    assert saved.price_cents == 349_990
    assert saved.source == "json-ld"


def test_price_above_target_is_persisted_and_not_reached():
    observations = Observations()
    result = execute(Targets(target()), Collector(collected(price_cents=350_001)), observations)
    assert result.target_reached is False
    assert observations.items[0].price_cents == 350_001


def test_missing_or_foreign_product_has_same_failure_without_side_effects():
    collector = Collector()
    observations = Observations()
    with pytest.raises(ApplicationError) as raised:
        execute(Targets(None), collector, observations)
    assert raised.value.code == "product_not_found"
    assert collector.calls == []
    assert observations.items == []


@pytest.mark.parametrize("changes", [
    {"telegram_user_id": 0}, {"telegram_user_id": True},
    {"product_id": "bad"}, {"observation_id": "bad"},
    {"observed_at": datetime(2026, 9, 16, 18, 0)},
])
def test_invalid_input_stops_before_repositories(changes):
    targets = Targets(target())
    observations = Observations()
    with pytest.raises(ApplicationError, match="Produto para verificação inválido"):
        execute(targets, Collector(), observations, **changes)
    assert targets.calls == []
    assert observations.items == []


@pytest.mark.parametrize("remote,expected", [
    ("access_blocked", "collection_blocked"),
    ("product_unavailable", "product_unavailable"),
    ("price_not_found", "price_not_found"),
    ("timeout", "collection_timeout"),
    ("forbidden_address", "collection_failed"),
])
def test_collection_failures_are_safely_mapped_and_persisted(remote, expected):
    observations = Observations()
    with pytest.raises(ApplicationError) as raised:
        execute(Targets(target()), Collector(error=ProductCollectionError(remote)), observations)
    assert raised.value.code == expected
    assert URL not in str(raised.value)
    saved = observations.items[0]
    assert saved.status == "failure"
    assert saved.error_code == expected
    assert saved.price_cents is None
    assert saved.source is None


def test_redirect_to_different_identity_persists_failure_without_remote_price():
    observations = Observations()
    with pytest.raises(ApplicationError) as raised:
        execute(Targets(target()), Collector(collected(external_id="MLB999")), observations)
    assert raised.value.code == "product_identity_changed"
    saved = observations.items[0]
    assert saved.status == "failure"
    assert saved.error_code == "product_identity_changed"
    assert saved.price_cents is None


def test_persistence_failure_prevents_success_result():
    with pytest.raises(RuntimeError, match="database unavailable"):
        execute(Targets(target()), Collector(collected()),
                Observations(error=RuntimeError("database unavailable")))


@pytest.mark.parametrize("changes", [
    {"product_id": "bad"}, {"product_key": "MLB999"},
    {"url": "https://evil.test/MLB-123"}, {"alias": " alias "},
    {"target_price_cents": 0}, {"target_price_cents": True},
])
def test_target_contract_rejects_invalid_repository_data(changes):
    with pytest.raises(ValueError, match="Alvo de verificação inválido"):
        target(**changes)
