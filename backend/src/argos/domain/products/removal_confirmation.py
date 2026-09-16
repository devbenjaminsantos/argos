"""Diagnóstico da confirmação textual, sem consultar propostas de terceiros."""
import re
from uuid import UUID


def removal_confirmation_error(text: str, version: UUID) -> str | None:
    normalized = text.strip().casefold()
    instruction = 'Copie a confirmação completa desta proposta ou use /cancelar.'
    if normalized == f'remover {version.hex}':
        return None
    parts = normalized.split()
    if not parts or parts[0] != 'remover' or len(parts) > 2:
        return f'Formato incorreto. Envie remover seguido do código da proposta. {instruction}'
    if len(parts) == 1:
        return f'Faltou o código de confirmação. {instruction}'
    code = parts[1]
    if not re.fullmatch('[0-9a-f]+', code):
        return f'Formato do código inválido. Use os 32 caracteres da proposta, sem hífens. {instruction}'
    if len(code) < 32:
        return f'Código incompleto. Copie todos os 32 caracteres. {instruction}'
    if len(code) > 32:
        return f'Código com tamanho inválido. Use exatamente 32 caracteres. {instruction}'
    if code != version.hex:
        return f'Código incorreto para esta proposta. {instruction}'
    return f'Formato incorreto. Separe remover e o código com um único espaço. {instruction}'
