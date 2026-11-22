"""Benign browser UI compatibility settings; no identity/fraud-signal spoofing."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrowserQAProfile:
    """A small set of presentation settings for deterministic UI tests."""

    viewport_width: int = 1365
    viewport_height: int = 768
    color_scheme: str = "light"
    reduced_motion: bool = False

    def __post_init__(self) -> None:
        if not (320 <= self.viewport_width <= 3840):
            raise ValueError("Viewport width must be between 320 and 3840 pixels.")
        if not (240 <= self.viewport_height <= 2160):
            raise ValueError("Viewport height must be between 240 and 2160 pixels.")
        if self.color_scheme not in {"light", "dark"}:
            raise ValueError("Color scheme must be 'light' or 'dark'.")
        if not isinstance(self.reduced_motion, bool):
            raise ValueError("reduced_motion must be a boolean.")
