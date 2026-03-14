"""Integration tests for the tool orchestration layer (US2).

Tests capability listing, provider detection, and error handling.
"""

from __future__ import annotations

import pytest

from print3d_skill import get_capability, list_capabilities, refresh_capabilities
from print3d_skill.exceptions import CapabilityUnavailable


class TestListCapabilities:
    def test_returns_all_six_capabilities(self):
        caps = list_capabilities()
        names = {c.name for c in caps}
        expected = {
            "mesh_loading",
            "mesh_analysis",
            "boolean_operations",
            "cad_compilation",
            "cad_rendering",
        }
        # At minimum, all registered capabilities must appear
        assert expected.issubset(names)

    def test_core_capabilities_always_available(self):
        caps = list_capabilities()
        core_caps = [c for c in caps if c.tier == "core"]
        for cap in core_caps:
            assert cap.is_available, f"Core capability '{cap.name}' should be available"

    def test_capability_has_required_fields(self):
        caps = list_capabilities()
        for cap in caps:
            assert cap.name
            assert cap.tier in ("core", "extended")


class TestGetCapability:
    def test_mesh_loading_returns_provider(self):
        provider = get_capability("mesh_loading")
        assert provider.name == "trimesh"
        assert provider.is_available

    def test_mesh_analysis_returns_provider(self):
        provider = get_capability("mesh_analysis")
        assert provider.name == "trimesh"

    def test_boolean_operations_returns_provider(self):
        provider = get_capability("boolean_operations")
        assert provider.name == "manifold3d"

    def test_unknown_capability_raises_error(self):
        with pytest.raises(CapabilityUnavailable) as exc_info:
            get_capability("nonexistent_capability")
        assert "nonexistent_capability" in str(exc_info.value)


class TestRefresh:
    def test_refresh_returns_capabilities(self):
        caps = refresh_capabilities()
        assert len(caps) > 0
        # Core caps should still be available after refresh
        core = [c for c in caps if c.tier == "core"]
        for cap in core:
            assert cap.is_available


class TestProviderVersions:
    def test_trimesh_has_version(self):
        provider = get_capability("mesh_loading")
        assert provider.get_version() is not None
