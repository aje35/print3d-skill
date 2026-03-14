"""Tool capability and provider status data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ToolCapability:
    """A named capability that the system can provide."""

    name: str
    description: str
    tier: str  # "core" or "extended"
    provider_name: str | None = None
    is_available: bool = False
    install_instructions: str | None = None


@dataclass
class ToolProviderInfo:
    """Status information about a tool provider."""

    name: str
    capabilities: list[str]
    tier: str  # "core" or "extended"
    is_available: bool = False
    version: str | None = None
    detection_method: str = ""
    install_instructions: str = ""
