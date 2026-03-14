"""Contract tests for the public API surface.

Verifies all 7 public functions exist with correct signatures,
all 7 exception classes exist, and all dataclass return types
are importable — per contracts/api.md.
"""

from __future__ import annotations

import inspect

import pytest


class TestPublicFunctions:
    """Verify all 7 public functions are importable with correct signatures."""

    def test_render_preview_signature(self):
        from print3d_skill import render_preview

        sig = inspect.signature(render_preview)
        params = list(sig.parameters.keys())
        assert "mesh_path" in params
        assert "output_path" in params
        assert "resolution" in params
        assert "timeout_seconds" in params
        # Check defaults
        assert sig.parameters["resolution"].default == (1600, 1200)
        assert sig.parameters["timeout_seconds"].default == 30.0

    def test_get_capability_signature(self):
        from print3d_skill import get_capability

        sig = inspect.signature(get_capability)
        assert "name" in sig.parameters

    def test_list_capabilities_signature(self):
        from print3d_skill import list_capabilities

        sig = inspect.signature(list_capabilities)
        assert len(sig.parameters) == 0

    def test_refresh_capabilities_signature(self):
        from print3d_skill import refresh_capabilities

        sig = inspect.signature(refresh_capabilities)
        assert len(sig.parameters) == 0

    def test_query_knowledge_signature(self):
        from print3d_skill import query_knowledge

        sig = inspect.signature(query_knowledge)
        params = list(sig.parameters.keys())
        assert "mode" in params
        assert "material" in params
        assert "printer" in params
        assert "problem_type" in params
        # All should default to None
        for p in params:
            assert sig.parameters[p].default is None

    def test_route_signature(self):
        from print3d_skill import route

        sig = inspect.signature(route)
        assert "mode" in sig.parameters

    def test_system_info_signature(self):
        from print3d_skill import system_info

        sig = inspect.signature(system_info)
        assert len(sig.parameters) == 0


class TestExceptionHierarchy:
    """Verify all 7 exception classes exist and inherit correctly."""

    def test_base_exception_exists(self):
        from print3d_skill.exceptions import Print3DSkillError

        assert issubclass(Print3DSkillError, Exception)

    @pytest.mark.parametrize(
        "exc_name",
        [
            "MeshLoadError",
            "UnsupportedFormatError",
            "RenderTimeoutError",
            "ScadCompileError",
            "CapabilityUnavailable",
            "InvalidModeError",
            "KnowledgeSchemaError",
        ],
    )
    def test_exception_inherits_from_base(self, exc_name):
        from print3d_skill import exceptions

        exc_class = getattr(exceptions, exc_name)
        from print3d_skill.exceptions import Print3DSkillError

        assert issubclass(exc_class, Print3DSkillError)


class TestReturnTypes:
    """Verify all dataclass return types are importable."""

    def test_preview_result(self):
        from print3d_skill.models.preview import PreviewResult

        assert hasattr(PreviewResult, "__dataclass_fields__")

    def test_view_angle(self):
        from print3d_skill.models.preview import ViewAngle

        assert hasattr(ViewAngle, "__dataclass_fields__")

    def test_tool_capability(self):
        from print3d_skill.models.capability import ToolCapability

        assert hasattr(ToolCapability, "__dataclass_fields__")

    def test_knowledge_file(self):
        from print3d_skill.models.knowledge import KnowledgeFile

        assert hasattr(KnowledgeFile, "__dataclass_fields__")

    def test_mode_response(self):
        from print3d_skill.models.mode import ModeResponse

        assert hasattr(ModeResponse, "__dataclass_fields__")

    def test_system_info(self):
        from print3d_skill.models.mode import SystemInfo

        assert hasattr(SystemInfo, "__dataclass_fields__")

    def test_mesh_file(self):
        from print3d_skill.models.mesh import MeshFile

        assert hasattr(MeshFile, "__dataclass_fields__")

    def test_bounding_box(self):
        from print3d_skill.models.mesh import BoundingBox

        assert hasattr(BoundingBox, "__dataclass_fields__")
