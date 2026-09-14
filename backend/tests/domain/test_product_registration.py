import pytest
from argos.domain.products.registration import validate_product_registration,parse_registration_confirmation

_DATA={"url":"https://mercadolivre.com.br/p/MLB123#tracking","alias":" Caneca   Kitty ","target_price_cents":15000,"interval_hours":12}


def test_validates_full_proposal_without_mutating_draft():
    result=validate_product_registration(_DATA)
    assert result.url=="https://mercadolivre.com.br/p/MLB123"
    assert result.alias=="Caneca Kitty"
    assert result.target_price_cents==15000
    assert result.interval_hours==12
    assert _DATA["alias"]==" Caneca   Kitty "


@pytest.mark.parametrize("changes", [{"url":None},{"url":"https://evil.test/p/MLB123"},{"alias":""},{"alias":"x"*61},{"target_price_cents":True},{"target_price_cents":0},{"target_price_cents":150.0},{"target_price_cents":1000000000},{"interval_hours":True},{"interval_hours":"12"},{"interval_hours":6}])
def test_invalid_stored_fields_are_rejected(changes):
    with pytest.raises(ValueError): validate_product_registration(_DATA|changes)


@pytest.mark.parametrize("key",list(_DATA))
def test_incomplete_draft_is_rejected(key):
    with pytest.raises(ValueError): validate_product_registration({k:v for k,v in _DATA.items() if k!=key})


@pytest.mark.parametrize("raw,expected",[("confirmar","confirmar"),(" CORRIGIR ","corrigir"),("CONFIRMAR","confirmar")])
def test_confirmation_actions(raw,expected):
    assert parse_registration_confirmation(raw)==expected


@pytest.mark.parametrize("raw",["sim","confirmar agora","/cancelar","",None])
def test_unknown_confirmation_is_rejected(raw):
    with pytest.raises(ValueError): parse_registration_confirmation(raw)
