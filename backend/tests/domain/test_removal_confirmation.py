from uuid import UUID
import pytest
from argos.domain.products.removal_confirmation import removal_confirmation_error

VERSION = UUID('12345678123456781234567812345678')

@pytest.mark.parametrize('raw,expected', [
    ('remover', 'Faltou o código'), ('confirmar', 'Formato incorreto'),
    ('remover abc', 'Código incompleto'), ('remover xyz', 'Formato do código inválido'),
    ('remover ' + 'a' * 33, 'tamanho inválido'),
    ('remover ' + 'a' * 32, 'Código incorreto'),
    ('remover ' + str(VERSION), 'sem hífens'),
    ('remover ' + VERSION.hex + ' extra', 'Formato incorreto'),
    ('remover  ' + VERSION.hex, 'único espaço'),
])
def test_distinct_feedback(raw, expected):
    assert expected in removal_confirmation_error(raw, VERSION)


def test_exact_confirmation_and_case_are_preserved():
    assert removal_confirmation_error(' REMOVER ' + VERSION.hex + ' ', VERSION) is None
