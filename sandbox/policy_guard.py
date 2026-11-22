"""Guardrails for synthetic QA inputs and unmistakable simulation labeling."""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence


FORBIDDEN_FIELD_NAMES = {
    "pan", "card", "card_number", "cardnumber", "cc", "cvv", "cvc",
    "expiry", "expiration", "track", "magstripe", "payment_credential",
}
_LONG_DIGIT_SEQUENCE = re.compile(r"(?<!\d)\d{13,19}(?!\d)")
SIMULATION_LABEL = "SIMULATION ONLY — NOT A REAL CARD OR AUTHENTICATION RESULT"


def assert_synthetic_payload(payload: Mapping[str, object]) -> None:
    """Reject payment-card fields and PAN-like digit sequences, recursively."""
    def visit(value: object, key: str = "") -> None:
        normalized = re.sub(r"[^a-z0-9]", "", key.lower())
        if normalized in {re.sub(r"[^a-z0-9]", "", item) for item in FORBIDDEN_FIELD_NAMES}:
            raise ValueError("Payment-card fields are not accepted in the QA sandbox.")
        if isinstance(value, Mapping):
            for child_key, child_value in value.items():
                visit(child_value, str(child_key))
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for child in value:
                visit(child)
        elif isinstance(value, str) and _LONG_DIGIT_SEQUENCE.search(value):
            raise ValueError("PAN-like numeric data is not accepted in the QA sandbox.")
    visit(payload)


def simulation_label() -> str:
    """Return the mandatory label for every synthetic result or report."""
    return SIMULATION_LABEL
