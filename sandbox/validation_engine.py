"""Strict validation for synthetic 3-D Secure simulation records."""
import re

TEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
SCENARIOS = {
    "frictionless_success",
    "challenge_required",
    "challenge_failed",
    "not_enrolled",
    "unavailable",
}
REQUIRED_COLUMNS = {"test_id", "scenario"}


def validate_simulation_record(record: dict[str, str]) -> dict[str, str]:
    """Accept only an opaque synthetic test ID and a known mock scenario."""
    if set(record) != REQUIRED_COLUMNS:
        raise ValueError("Simulation rows must contain exactly test_id and scenario columns.")
    test_id = (record.get("test_id") or "").strip()
    scenario = (record.get("scenario") or "").strip().lower()
    if not TEST_ID.fullmatch(test_id):
        raise ValueError("test_id must be 1–32 letters, digits, underscores, or hyphens.")
    if scenario not in SCENARIOS:
        raise ValueError("Unknown mock scenario. Use one of the documented synthetic scenarios.")
    return {"test_id": test_id, "scenario": scenario}
