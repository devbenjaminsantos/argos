"""Erros públicos produzidos pelos casos de uso."""


class ApplicationError(Exception):
    """Falha esperada que pode ser traduzida com segurança pela camada de entrada."""

    def __init__(self, code: str, public_message: str) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message
