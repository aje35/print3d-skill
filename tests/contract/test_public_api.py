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


class TestF2PublicFunctions:
    """Verify F2 public functions are importable with correct signatures."""

    def test_analyze_mesh_signature(self):
        from print3d_skill import analyze_mesh

        sig = inspect.signature(analyze_mesh)
        params = list(sig.parameters.keys())
        assert "mesh_path" in params
        assert "config" in params

    def test_repair_mesh_signature(self):
        from print3d_skill import repair_mesh

        sig = inspect.signature(repair_mesh)
        params = list(sig.parameters.keys())
        assert "mesh_path" in params
        assert "output_path" in params
        assert "config" in params

    def test_export_mesh_signature(self):
        from print3d_skill import export_mesh

        sig = inspect.signature(export_mesh)
        params = list(sig.parameters.keys())
        assert "mesh_path" in params
        assert "output_dir" in params
        assert "formats" in params


class TestF2Exceptions:
    """Verify F2-specific exceptions exist and inherit from Print3DSkillError."""

    @pytest.mark.parametrize("exc_name", [
        "MeshAnalysisError", "RepairError", "ExportError",
    ])
    def test_f2_exception_inherits_from_base(self, exc_name):
        from print3d_skill import exceptions
        from print3d_skill.exceptions import Print3DSkillError

        exc_class = getattr(exceptions, exc_name)
        assert issubclass(exc_class, Print3DSkillError)


class TestF2ReturnTypes:
    """Verify F2 return types are importable dataclasses."""

    def test_mesh_analysis_report(self):
        from print3d_skill.models.analysis import MeshAnalysisReport

        assert hasattr(MeshAnalysisReport, "__dataclass_fields__")

    def test_repair_summary(self):
        from print3d_skill.models.repair import RepairSummary

        assert hasattr(RepairSummary, "__dataclass_fields__")

    def test_repair_result(self):
        from print3d_skill.models.repair import RepairResult

        assert hasattr(RepairResult, "__dataclass_fields__")

    def test_repair_config(self):
        from print3d_skill.models.repair import RepairConfig

        assert hasattr(RepairConfig, "__dataclass_fields__")

    def test_export_result(self):
        from print3d_skill.models.export import ExportResult

        assert hasattr(ExportResult, "__dataclass_fields__")

    def test_mesh_defect(self):
        from print3d_skill.models.analysis import MeshDefect

        assert hasattr(MeshDefect, "__dataclass_fields__")

    def test_shell_analysis(self):
        from print3d_skill.models.analysis import ShellAnalysis

        assert hasattr(ShellAnalysis, "__dataclass_fields__")


class TestF2Enums:
    """Verify F2 enums have the correct number of members."""

    def test_defect_type_has_10_values(self):
        from print3d_skill.models.analysis import DefectType

        assert len(DefectType) == 10

    def test_repair_strategy_has_6_values(self):
        from print3d_skill.models.repair import RepairStrategy

        assert len(RepairStrategy) == 6

    def test_defect_severity_has_3_values(self):
        from print3d_skill.models.analysis import DefectSeverity

        assert len(DefectSeverity) == 3

    def test_health_classification_has_3_values(self):
        from print3d_skill.models.analysis import MeshHealthClassification

        assert len(MeshHealthClassification) == 3


class TestF3PublicFunctions:
    """Verify F3 public functions are importable with correct signatures."""

    def test_create_design_signature(self):
        from print3d_skill import create_design

        sig = inspect.signature(create_design)
        params = list(sig.parameters.keys())
        assert "request" in params
        assert "config" in params

    def test_validate_printability_signature(self):
        from print3d_skill import validate_printability

        sig = inspect.signature(validate_printability)
        params = list(sig.parameters.keys())
        assert "mesh_path" in params
        assert "config" in params

    def test_start_session_signature(self):
        from print3d_skill.create import start_session

        sig = inspect.signature(start_session)
        params = list(sig.parameters.keys())
        assert "request" in params
        assert "config" in params

    def test_submit_iteration_signature(self):
        from print3d_skill.create import submit_iteration

        sig = inspect.signature(submit_iteration)
        params = list(sig.parameters.keys())
        assert "session" in params
        assert "scad_code" in params
        assert "changes" in params

    def test_export_design_signature(self):
        from print3d_skill.create import export_design

        sig = inspect.signature(export_design)
        params = list(sig.parameters.keys())
        assert "session" in params
        assert "output_dir" in params

    def test_detect_bosl2_signature(self):
        from print3d_skill.create.bosl2 import detect_bosl2

        sig = inspect.signature(detect_bosl2)
        assert len(sig.parameters) == 0


class TestF3Exceptions:
    """Verify F3-specific exceptions exist and inherit from Print3DSkillError."""

    @pytest.mark.parametrize("exc_name", ["DesignError", "PrintabilityError"])
    def test_f3_exception_inherits_from_base(self, exc_name):
        from print3d_skill import exceptions
        from print3d_skill.exceptions import Print3DSkillError

        exc_class = getattr(exceptions, exc_name)
        assert issubclass(exc_class, Print3DSkillError)


class TestF3ReturnTypes:
    """Verify F3 return types are importable dataclasses."""

    @pytest.mark.parametrize("type_name", [
        "CreateConfig",
        "CreateResult",
        "CreateSession",
        "DesignExport",
        "DesignRequest",
        "GeneratedDesign",
        "PrintabilityReport",
        "PrintabilityWarning",
    ])
    def test_f3_type_is_dataclass(self, type_name):
        from print3d_skill import models

        cls = getattr(models, type_name)
        assert hasattr(cls, "__dataclass_fields__")


class TestF3PrintabilityIdempotency:
    """Verify validate_printability on a print-ready mesh returns is_printable=True."""

    def test_print_ready_mesh(self, clean_mesh):
        from print3d_skill import validate_printability
        from print3d_skill.models.create import CreateConfig

        # Use generous thresholds so the clean mesh passes
        config = CreateConfig(
            min_wall_thickness=0.1,
            max_overhang_angle=89.0,
            max_bridge_distance=1000.0,
            min_bed_adhesion_area=0.0,
        )
        report = validate_printability(str(clean_mesh), config)
        assert report.is_printable is True


class TestF2Idempotency:
    """Verify repair_mesh on an already-clean mesh is a no-op."""

    def test_repair_clean_mesh_is_noop(self, clean_mesh):
        from print3d_skill import repair_mesh
        from print3d_skill.models.repair import RepairConfig

        summary = repair_mesh(str(clean_mesh), config=RepairConfig(render_previews=False))
        assert summary.total_defects_found == 0
        assert summary.total_defects_fixed == 0
        assert len(summary.repairs) == 0
