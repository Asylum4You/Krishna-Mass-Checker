"""Deterministic mock 3-D Secure outcomes; never contacts payment systems."""
from .validation_engine import SCENARIOS

MOCK_OUTCOMES = {
    "frictionless_success": ("SIMULATED_AUTHENTICATED", "Mock frictionless flow completed successfully."),
    "challenge_required": ("SIMULATED_CHALLENGE_REQUIRED", "Mock issuer requests a challenge; no challenge is performed."),
    "challenge_failed": ("SIMULATED_CHALLENGE_FAILED", "Mock challenge result is failed; no challenge is performed."),
    "not_enrolled": ("SIMULATED_NOT_ENROLLED", "Mock directory response indicates not enrolled."),
    "unavailable": ("SIMULATED_UNAVAILABLE", "Mock directory or issuer service is unavailable."),
}


def simulate_3ds(scenario: str) -> dict[str, str]:
    """Return a labeled synthetic outcome for a predefined scenario only."""
    if scenario not in SCENARIOS:
        raise ValueError("Unsupported synthetic scenario.")
    status, detail = MOCK_OUTCOMES[scenario]
    return {
        "scenario": scenario,
        "result": status,
        "detail": detail,
        "mode": "SIMULATION ONLY — NOT A REAL CARD OR AUTHENTICATION RESULT",
    }
