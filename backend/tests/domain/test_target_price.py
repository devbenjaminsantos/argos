import pytest
from argos.domain.target_price import parse_target_price_cents, format_target_price_brl


@pytest.mark.parametrize("raw,cents", [("2500",250000),("2500,90",250090),("R$ 2.500,90",250090),("0,01",1),("1,5",150),("  R$2500  ",250000),("9.999.999,99",999999999)])
def test_parses_exact_cents(raw,cents):
    assert parse_target_price_cents(raw) == cents


@pytest.mark.parametrize("raw", ["0","0,00","-1","+1","1.50","1,234","1,000.00","1e3","NaN","Infinity","2.50,00","10.000.000", "R$  2", "1\n2", "", None, "x"*65, "１２"])
def test_rejects_invalid_ambiguous_and_out_of_range_prices(raw):
    with pytest.raises(ValueError):
        parse_target_price_cents(raw)


def test_formats_brl_without_float():
    assert format_target_price_brl(250090) == "R$ 2.500,90"
    assert format_target_price_brl(1) == "R$ 0,01"


@pytest.mark.parametrize("cents", [True,0,-1,1000000000,1.1])
def test_formatter_rejects_invalid_cents(cents):
    with pytest.raises(ValueError):
        format_target_price_brl(cents)
