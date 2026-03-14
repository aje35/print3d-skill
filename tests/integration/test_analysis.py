"""Integration tests for the analyze_mesh() public API (US6).

End-to-end tests that exercise the full analysis pipeline including
format detection, mesh loading, defect detection, and report building.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from print3d_skill.analysis import analyze_mesh
from print3d_skill.exceptions import MeshLoadError, UnsupportedFormatError
from print3d_skill.models.analysis import (
    DefectType,
    MeshAnalysisReport,
    MeshHealthClassification,
)


# ---------------------------------------------------------------------------
# Clean mesh
# ---------------------------------------------------------------------------

class TestAnalyzeCleanMesh:
    def test_clean_mesh_is_print_ready(self, clean_mesh: Path):
        report = analyze_mesh(str(clean_mesh))
        assert isinstance(report, MeshAnalysisReport)
        assert report.classification == MeshHealthClassification.print_ready
        assert len(report.defects) == 0
        assert report.health_score == 1.0

    def test_clean_mesh_metadata(self, clean_mesh: Path):
        report = analyze_mesh(str(clean_mesh))
        assert report.format == "stl"
        assert report.vertex_count > 0
        assert report.face_count > 0
        assert report.is_triangulated is True
        assert report.shell_count == 1


# ---------------------------------------------------------------------------
# Mesh with holes (boundary edges)
# ---------------------------------------------------------------------------

class TestAnalyzeMeshWithHoles:
    def test_detects_boundary_edges(self, mesh_with_holes: Path):
        report = analyze_mesh(str(mesh_with_holes))
        defect_types = {d.defect_type for d in report.defects}
        assert DefectType.boundary_edges in defect_types

    def test_boundary_edges_are_critical(self, mesh_with_holes: Path):
        report = analyze_mesh(str(mesh_with_holes))
        boundary = [
            d for d in report.defects
            if d.defect_type == DefectType.boundary_edges
        ]
        assert len(boundary) == 1
        assert boundary[0].severity.value == "critical"
        assert boundary[0].count > 0


# ---------------------------------------------------------------------------
# Mesh with bad normals
# ---------------------------------------------------------------------------

class TestAnalyzeMeshWithBadNormals:
    def test_detects_inconsistent_normals(self, mesh_with_bad_normals: Path):
        report = analyze_mesh(str(mesh_with_bad_normals))
        defect_types = {d.defect_type for d in report.defects}
        assert DefectType.inconsistent_normals in defect_types

    def test_inconsistent_normals_are_warning(self, mesh_with_bad_normals: Path):
        report = analyze_mesh(str(mesh_with_bad_normals))
        normals_defect = [
            d for d in report.defects
            if d.defect_type == DefectType.inconsistent_normals
        ]
        assert len(normals_defect) == 1
        assert normals_defect[0].severity.value == "warning"
        assert normals_defect[0].count > 0


# ---------------------------------------------------------------------------
# Unsupported format
# ---------------------------------------------------------------------------

class TestUnsupportedFormat:
    def test_step_file_raises_unsupported(self, tmp_path: Path):
        step_file = tmp_path / "model.step"
        step_file.write_text("ISO-10303-21; fake step content")
        with pytest.raises(UnsupportedFormatError):
            analyze_mesh(str(step_file))

    def test_unknown_extension_raises_unsupported(self, tmp_path: Path):
        unknown = tmp_path / "model.xyz"
        unknown.write_text("not a mesh")
        with pytest.raises(UnsupportedFormatError):
            analyze_mesh(str(unknown))


# ---------------------------------------------------------------------------
# Nonexistent file
# ---------------------------------------------------------------------------

class TestNonexistentFile:
    def test_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            analyze_mesh("/nonexistent/path/model.stl")


# ---------------------------------------------------------------------------
# Multi-body mesh
# ---------------------------------------------------------------------------

class TestMultiBodyMesh:
    def test_shell_count_greater_than_one(self, mesh_multi_body: Path):
        report = analyze_mesh(str(mesh_multi_body))
        assert report.shell_count > 1

    def test_per_shell_analysis_populated(self, mesh_multi_body: Path):
        report = analyze_mesh(str(mesh_multi_body))
        assert len(report.shells) == report.shell_count
        for shell in report.shells:
            assert shell.vertex_count > 0
            assert shell.face_count > 0
            assert shell.bounding_box is not None


# ---------------------------------------------------------------------------
# Corrupt file
# ---------------------------------------------------------------------------

class TestCorruptFile:
    def test_corrupt_stl_raises_mesh_load_error(self, corrupt_stl: Path):
        with pytest.raises(MeshLoadError):
            analyze_mesh(str(corrupt_stl))
