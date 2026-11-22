"""PII-minimized audit event builder for synthetic QA runs."""
from __future__ import annotations

from datetime import datetime, timezone
import re


_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")


def build_audit_event(
    *,
    test_id: str,
    environment: str,
    outcome: str,
    timestamp: datetime | None = None,
) -> dict[str, str]:
    """Build a compact audit record; caller supplies labels, never card/user data."""
    values = {"test_id": test_id, "environment": environment, "outcome": outcome}
    if any(not isinstance(value, str) or not _SAFE_TOKEN.fullmatch(value) for value in values.values()):
        raise ValueError("Audit fields must be short, opaque labels without personal or payment data.")
    moment = timestamp or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise ValueError("Audit timestamps must be timezone-aware.")
    return {
        "test_id": test_id,
        "environment": environment,
        "timestamp": moment.astimezone(timezone.utc).isoformat(),
        "outcome": outcome,
        "mode": "SIMULATION ONLY",
    }
