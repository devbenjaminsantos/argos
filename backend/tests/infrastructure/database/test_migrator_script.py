"""Contrato de segurança da validação do executor de migrações."""

from pathlib import Path


def test_migrator_validation_always_rolls_back() -> None:
    source = (
        Path(__file__).parents[3] / "scripts" / "validate_migrator.py"
    ).read_text(encoding="utf-8")

    assert 'text("SET ROLE argos_migrator")' in source
    assert "transaction.rollback()" in source
    assert "transaction.commit()" not in source
