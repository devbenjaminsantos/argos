"""Grafo de conversa impede saltar confirmação e fluxos."""

import pytest
from argos.domain.telegram_conversation import validate_conversation_transition


@pytest.mark.parametrize(("current", "following"), [
    ("awaiting_url", "awaiting_confirmation"),
    ("awaiting_alias", "awaiting_removal_confirmation"),
    ("unknown", "awaiting_url"),
    ("awaiting_confirmation", "awaiting_alias"),
])
def test_disallows_skipping_steps_or_switching_flows(current, following):
    with pytest.raises(ValueError):
        validate_conversation_transition(current, following)


def test_registration_steps_and_correction_are_allowed():
    states = ["awaiting_url", "awaiting_alias", "awaiting_target_price",
              "awaiting_interval", "awaiting_confirmation", "awaiting_url"]
    for current, following in zip(states, states[1:]):
        validate_conversation_transition(current, following)
