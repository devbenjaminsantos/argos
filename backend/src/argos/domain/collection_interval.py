"""Intervalos permitidos no piloto."""


def parse_collection_interval_hours(raw: str) -> int:
    if not isinstance(raw, str) or raw.strip() not in {"12", "24"}:
        raise ValueError("Intervalo inválido.")
    return int(raw.strip())
