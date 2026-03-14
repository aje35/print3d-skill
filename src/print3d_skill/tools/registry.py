"""Capability registry for tool discovery.

Manages registered providers and maps capability names to providers.
Detection is lazy — providers are only checked on first query.
"""

from __future__ import annotations

from print3d_skill.exceptions import CapabilityUnavailable
from print3d_skill.models.capability import ToolCapability
from print3d_skill.tools.base import ToolProvider


class ToolRegistry:
    """Singleton-style registry holding tool providers.

    Providers register their capabilities. Callers query by
    capability name to get the appropriate provider.
    """

    def __init__(self) -> None:
        self._providers: list[ToolProvider] = []
        self._capability_map: dict[str, ToolProvider] = {}

    def register(self, provider: ToolProvider) -> None:
        """Register a tool provider and map its capabilities."""
        self._providers.append(provider)
        for cap in provider.get_capabilities():
            self._capability_map[cap] = provider

    def get(self, capability_name: str) -> ToolProvider:
        """Get the provider for a named capability.

        Raises CapabilityUnavailable if no provider offers this
        capability or the provider is not available.
        """
        provider = self._capability_map.get(capability_name)
        if provider is None:
            raise CapabilityUnavailable(
                capability=capability_name,
                provider="",
                install_instructions="No provider registered for this capability.",
            )

        if not provider.is_available:
            raise CapabilityUnavailable(
                capability=capability_name,
                provider=provider.name,
                install_instructions=provider.install_instructions,
            )

        return provider

    def list_all(self) -> list[ToolCapability]:
        """List all known capabilities and their availability status."""
        capabilities: list[ToolCapability] = []
        for cap_name, provider in self._capability_map.items():
            capabilities.append(
                ToolCapability(
                    name=cap_name,
                    description=f"Provided by {provider.name}",
                    tier=provider.tier,
                    provider_name=provider.name if provider.is_available else None,
                    is_available=provider.is_available,
                    install_instructions=(
                        None if provider.is_available
                        else provider.install_instructions
                    ),
                )
            )
        return capabilities

    def refresh(self) -> list[ToolCapability]:
        """Re-detect all tool availability and return updated list."""
        for provider in self._providers:
            provider.refresh()
        return self.list_all()
