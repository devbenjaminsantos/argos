import pytest
from argos.domain.collection_interval import parse_collection_interval_hours


@pytest.mark.parametrize("raw,expected", [("12",12),("24",24),(" 12 ",12)])
def test_accepts_supported_hours(raw,expected):
    assert parse_collection_interval_hours(raw) == expected


@pytest.mark.parametrize("raw", ["0","6","48","12h","24 horas","12.0","012","+12","",None,12,True])
def test_rejects_other_values_and_formats(raw):
    with pytest.raises(ValueError):
        parse_collection_interval_hours(raw)
