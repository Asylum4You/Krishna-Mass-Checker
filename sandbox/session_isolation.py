"""In-memory isolation identifiers for synthetic QA runs; no browser profiles."""
from __future__ import annotations

from dataclasses import dataclass
import re
from uuid import uuid4


TEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


@dataclass(frozen=True)
class SyntheticSession:
    test_id: str
    session_id: str
    storage_mode: str = "IN_MEMORY_ONLY"
    mode: str = "SIMULATION ONLY"


def create_synthetic_session(test_id: str) -> SyntheticSession:
    """Create an isolated, ephemeral session label for a synthetic test case."""
    if not TEST_ID_PATTERN.fullmatch(test_id):
        raise ValueError("test_id must be an opaque synthetic identifier (1–40 safe characters).")
    return SyntheticSession(test_id=test_id, session_id=uuid4().hex)
