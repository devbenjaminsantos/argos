"""Transições permitidas sem dependência de banco ou Telegram."""

_TRANSITIONS = {
    "awaiting_url": ("awaiting_alias",),
    "awaiting_alias": ("awaiting_target_price",),
    "awaiting_target_price": ("awaiting_interval",),
    "awaiting_interval": ("awaiting_confirmation",),
    "awaiting_confirmation": ("awaiting_url",),
    "awaiting_product_to_remove": ("awaiting_removal_confirmation",),
}


def validate_conversation_transition(current: str, following: str) -> None:
    if following not in _TRANSITIONS.get(current, ()):
        raise ValueError("Transição conversacional inválida.")
