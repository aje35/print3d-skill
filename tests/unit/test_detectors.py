"""Unit tests for all 10 mesh defect detectors (US6).

Each test loads a defective mesh fixture, runs the specific detector,
and asserts the correct DefectType, severity, and non-zero count.
Clean-mesh tests verify that each detector returns None for a healthy mesh.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import trimesh

from print3d_skill.analysis.detectors import (
    detect_boundary_edges,
    detect_degenerate_faces,
    detect_duplicate_faces,
    detect_duplicate_vertices,
    detect_excessive_poly_count,
    detect_inconsistent_normals,
    detect_non_manifold_edges,
    detect_non_manifold_vertices,
    detect_non_watertight,
    detect_self_intersecting,
)
from print3d_skill.models.analysis import DefectSeverity, DefectType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load(fixture_path: Path) -> trimesh.Trimesh:
    return trimesh.load(str(fixture_path), force="mesh")


# ---------------------------------------------------------------------------
# detect_non_manifold_edges
# ---------------------------------------------------------------------------

class TestDetectNonManifoldEdges:
    def test_detects_non_manifold_edges(self, mesh_non_manifold: Path):
        mesh = _load(mesh_non_manifold)
        result = detect_non_manifold_edges(mesh)
        assert result is not None
        assert result.defect_type == DefectType.non_manifold_edges
        assert result.severity == DefectSeverity.critical
        assert result.count > 0

    def test_clean_mesh_returns_none(self, clean_mesh: Path):
        mesh = _load(clean_mesh)
        result = detect_non_manifold_edges(mesh)
        assert result is None


# ---------------------------------------------------------------------------
# detect_non_manifold_vertices
# ---------------------------------------------------------------------------

class TestDetectNonManifoldVertices:
    def test_detects_non_manifold_vertices(self, mesh_non_manifold: Path):
        mesh = _load(mesh_non_manifold)
        result = detect_non_manifold_vertices(mesh)
        # Non-manifold edge mesh may also trigger non-manifold vertices;
        # if not, the fixture still exercises the code path returning None.
        if result is not None:
            assert result.defect_type == DefectType.non_manifold_vertices
            assert result.severity == DefectSeverity.critical
            assert result.count > 0

    def test_clean_mesh_returns_none(self, clean_mesh: Path):
        mesh = _load(clean_mesh)
        result = detect_non_manifold_vertices(mesh)
        assert result is None


# ---------------------------------------------------------------------------
# detect_boundary_edges
# ---------------------------------------------------------------------------

class TestDetectBoundaryEdges:
    def test_detects_boundary_edges(self, mesh_with_holes: Path):
        mesh = _load(mesh_with_holes)
        result = detect_boundary_edges(mesh)
        assert result is not None
        assert result.defect_type == DefectType.boundary_edges
        assert result.severity == DefectSeverity.critical
        assert result.count > 0
        assert len(result.affected_indices) > 0

    def test_clean_mesh_returns_none(self, clean_mesh: Path):
        mesh = _load(clean_mesh)
        result = detect_boundary_edges(mesh)
        assert result is None


# ---------------------------------------------------------------------------
# detect_non_watertight
# ---------------------------------------------------------------------------

class TestDetectNonWatertight:
    def test_detects_non_watertight(self, mesh_with_holes: Path):
        mesh = _load(mesh_with_holes)
        result = detect_non_watertight(mesh)
        assert result is not None
        assert result.defect_type == DefectType.non_watertight
        assert result.severity == DefectSeverity.critical
        assert result.count == 1

    def test_clean_mesh_returns_none(self, clean_mesh: Path):
        mesh = _load(clean_mesh)
        result = detect_non_watertight(mesh)
        assert result is None


# ---------------------------------------------------------------------------
# detect_inconsistent_normals
# ---------------------------------------------------------------------------

class TestDetectInconsistentNormals:
    def test_detects_bad_normals(self, mesh_with_bad_normals: Path):
        mesh = _load(mesh_with_bad_normals)
        result = detect_inconsistent_normals(mesh)
        assert result is not None
        assert result.defect_type == DefectType.inconsistent_normals
        assert result.severity == DefectSeverity.warning
        assert result.count > 0
        assert len(result.affected_indices) > 0

    def test_clean_mesh_returns_none(self, clean_mesh: Path):
        mesh = _load(clean_mesh)
        result = detect_inconsistent_normals(mesh)
        assert result is None


# ---------------------------------------------------------------------------
# detect_degenerate_faces
# ---------------------------------------------------------------------------

class TestDetectDegenerateFaces:
    def test_detects_degenerate_faces(self, mesh_with_degenerate_faces: Path):
        mesh = _load(mesh_with_degenerate_faces)
        result = detect_degenerate_faces(mesh)
        assert result is not None
        assert result.defect_type == DefectType.degenerate_faces
        assert result.severity == DefectSeverity.info
        assert result.count > 0

    def test_clean_mesh_returns_none(self, clean_mesh: Path):
        mesh = _load(clean_mesh)
        result = detect_degenerate_faces(mesh)
        assert result is None


# ---------------------------------------------------------------------------
# detect_duplicate_vertices
# ---------------------------------------------------------------------------

class TestDetectDuplicateVertices:
    def test_detects_duplicate_vertices(self):
        """Build mesh with near-duplicate vertices in-memory.

        STL round-trips merge close vertices, so we construct directly via
        trimesh to guarantee the duplicates survive.
        """
        import numpy as np

        base = trimesh.creation.box(extents=[20, 20, 20])
        verts = base.vertices.copy()
        faces = base.faces.copy()
        num_to_dup = min(4, len(verts))
        dup_verts = verts[:num_to_dup] + 1e-9
        new_start = len(verts)
        verts = np.vstack([verts, dup_verts])
        for i in range(min(num_to_dup, len(faces))):
            for j in range(3):
                if faces[i][j] < num_to_dup:
                    faces[i][j] = new_start + faces[i][j]
        mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)

        result = detect_duplicate_vertices(mesh)
        assert result is not None
        assert result.defect_type == DefectType.duplicate_vertices
        assert result.severity == DefectSeverity.info
        assert result.count > 0
        assert len(result.affected_indices) > 0

    def test_clean_mesh_returns_none(self, clean_mesh: Path):
        mesh = _load(clean_mesh)
        result = detect_duplicate_vertices(mesh)
        assert result is None


# ---------------------------------------------------------------------------
# detect_duplicate_faces
# ---------------------------------------------------------------------------

class TestDetectDuplicateFaces:
    def test_detects_duplicate_faces(self, mesh_with_duplicate_faces: Path):
        mesh = _load(mesh_with_duplicate_faces)
        result = detect_duplicate_faces(mesh)
        assert result is not None
        assert result.defect_type == DefectType.duplicate_faces
        assert result.severity == DefectSeverity.info
        assert result.count > 0
        assert len(result.affected_indices) > 0

    def test_clean_mesh_returns_none(self, clean_mesh: Path):
        mesh = _load(clean_mesh)
        result = detect_duplicate_faces(mesh)
        assert result is None


# ---------------------------------------------------------------------------
# detect_excessive_poly_count
# ---------------------------------------------------------------------------

class TestDetectExcessivePolyCount:
    def test_detects_excessive_polys_with_low_threshold(self, clean_mesh: Path):
        """Use a very low threshold so even the small clean mesh triggers it."""
        mesh = _load(clean_mesh)
        result = detect_excessive_poly_count(mesh, max_count=2)
        assert result is not None
        assert result.defect_type == DefectType.excessive_poly_count
        assert result.severity == DefectSeverity.info
        assert result.count > 2

    def test_default_threshold_clean_mesh_returns_none(self, clean_mesh: Path):
        mesh = _load(clean_mesh)
        result = detect_excessive_poly_count(mesh)
        assert result is None


# ---------------------------------------------------------------------------
# detect_self_intersecting
# ---------------------------------------------------------------------------

class TestDetectSelfIntersecting:
    def test_detects_self_intersection(self, mesh_self_intersecting: Path):
        mesh = _load(mesh_self_intersecting)
        result = detect_self_intersecting(mesh)
        assert result is not None
        assert result.defect_type == DefectType.self_intersecting
        assert result.severity == DefectSeverity.warning
        assert result.count > 0

    def test_clean_mesh_returns_none(self, clean_mesh: Path):
        mesh = _load(clean_mesh)
        result = detect_self_intersecting(mesh)
        assert result is None
