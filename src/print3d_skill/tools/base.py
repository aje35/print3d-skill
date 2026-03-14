"""ToolProvider abstract base class.

Each tool provider implements detect() for lazy availability checking.
Detection is cached and can be refreshed via the registry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ToolProvider(ABC):
    """Base class for external tool wrappers.

    Subclasses must implement detect() and define their capabilities,
    tier, and install instructions.
    """

    name: str = ""
    tier: str = "core"
    install_instructions: str = ""
    detection_method: str = ""

    def __init__(self) -> None:
        self._detected: bool | None = None
        self._version: str | None = None

    @abstractmethod
    def detect(self) -> bool:
        """Check if the tool is available on this system.

        Returns True if the tool is detected and usable.
        Called lazily on first access and cached.
        """

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """Return the list of capability names this provider offers."""

    def get_version(self) -> str | None:
        """Return the detected version of the tool, if available."""
        return self._version

    @property
    def is_available(self) -> bool:
        """Whether the tool is detected and usable (lazy, cached)."""
        if self._detected is None:
            self._detected = self.detect()
        return self._detected

    def refresh(self) -> None:
        """Re-detect tool availability (clears cache)."""
        self._detected = None
        self._version = None
