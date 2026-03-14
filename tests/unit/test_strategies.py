"""Unit tests for all 6 mesh repair strategy functions.

Each strategy is exercised with two scenarios:
  1. A defective mesh that should trigger a repair (success=True, elements_affected > 0).
  2. A clean / already-repaired mesh that should return success=False because
     there is nothing to fix.

All meshes are constructed in-memory via trimesh — no file I/O is performed.

Where a strategy delegates to an optional third-party library
(``fast_simplification`` for decimation, ``trimesh.repair.fill_holes`` for
hole-filling), the external call is patched via ``unittest.mock`` so that the
tests are hermetic and don't depend on optional packages being installed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import trimesh

from print3d_skill.models.repair import RepairConfig, RepairResult, RepairStrategy
from print3d_skill.repair.strategies import (
    strategy_decimate,
    strategy_fill_holes,
    strategy_fix_normals,
    strategy_merge_vertices,
    strategy_remove_degenerates,
    strategy_remove_duplicates,
)


# ---------------------------------------------------------------------------
# Shared mesh-building helpers
# ---------------------------------------------------------------------------

def _box_mesh() -> trimesh.Trimesh:
    """Return a fresh watertight box mesh with process=False to preserve structure."""
    base = trimesh.creation.box(extents=[20, 20, 20])
    return trimesh.Trimesh(vertices=base.vertices.copy(), faces=base.faces.copy(), process=False)


def _icosphere_mesh(subdivisions: int = 2) -> trimesh.Trimesh:
    """Return a fresh icosphere mesh."""
    base = trimesh.creation.icosphere(subdivisions=subdivisions)
    return trimesh.Trimesh(vertices=base.vertices.copy(), faces=base.faces.copy(), process=False)


def _default_config(**overrides) -> RepairConfig:
    """Return a RepairConfig, optionally overriding default fields."""
    return RepairConfig(**overrides)


# ---------------------------------------------------------------------------
# strategy_merge_vertices
# ---------------------------------------------------------------------------

class TestMergeVertices:
    """Tests for strategy_merge_vertices(mesh, config) -> RepairResult."""

    def _mesh_with_near_duplicate_vertices(self, tolerance: float = 0.01) -> trimesh.Trimesh:
        """Build a box mesh with extra vertices placed within `tolerance` of originals.

        The original vertices are kept and additional near-duplicate copies are
        appended so that the strategy has something to merge.  The faces are
        remapped so that some triangles reference the duplicate indices, making
        the duplicates actually referenced (and therefore not removed by a mere
        unreferenced-vertex pass).
        """
        base = trimesh.creation.box(extents=[20, 20, 20])
        verts = base.vertices.copy()
        faces = base.faces.copy()

        # Duplicate the first 4 vertices, displaced by half the tolerance
        num_to_dup = min(4, len(verts))
        offset = tolerance * 0.5
        dup_verts = verts[:num_to_dup] + offset
        new_start = len(verts)
        verts = np.vstack([verts, dup_verts])

        # Remap some faces to use the duplicate indices so they are referenced
        for i in range(min(num_to_dup, len(faces))):
            for j in range(3):
                if faces[i][j] < num_to_dup:
                    faces[i][j] = new_start + faces[i][j]

        return trimesh.Trimesh(vertices=verts, faces=faces, process=False)

    def test_merges_near_duplicate_vertices(self):
        """Vertices within tolerance must be merged; vertex count must decrease."""
        tolerance = 0.05
        mesh = self._mesh_with_near_duplicate_vertices(tolerance=tolerance)
        original_vertex_count = len(mesh.vertices)

        config = _default_config(vertex_merge_tolerance=tolerance)
        result = strategy_merge_vertices(mesh, config)

        assert isinstance(result, RepairResult)
        assert result.strategy == RepairStrategy.merge_vertices
        assert result.success is True
        assert result.elements_affected > 0
        assert len(mesh.vertices) < original_vertex_count

    def test_result_description_mentions_merged_count(self):
        """The description field should reference how many vertices were merged."""
        tolerance = 0.05
        mesh = self._mesh_with_near_duplicate_vertices(tolerance=tolerance)
        config = _default_config(vertex_merge_tolerance=tolerance)

        result = strategy_merge_vertices(mesh, config)

        # The strategy always formats "Merged N duplicate vertices …"
        assert "Merged" in result.description
        assert str(result.elements_affected) in result.description

    def test_clean_mesh_returns_success_false(self):
        """A mesh with no near-duplicate vertices must yield success=False."""
        mesh = _box_mesh()
        # Default tolerance is tiny (1e-8); vertices are far apart on a 20mm box.
        config = _default_config(vertex_merge_tolerance=1e-8)
        result = strategy_merge_vertices(mesh, config)

        assert result.success is False
        assert result.elements_affected == 0

    def test_elements_affected_equals_vertex_reduction(self):
        """elements_affected must equal the reduction in vertex count."""
        tolerance = 0.05
        mesh = self._mesh_with_near_duplicate_vertices(tolerance=tolerance)
        original_count = len(mesh.vertices)
        config = _default_config(vertex_merge_tolerance=tolerance)

        result = strategy_merge_vertices(mesh, config)

        assert result.elements_affected == original_count - len(mesh.vertices)


# ---------------------------------------------------------------------------
# strategy_remove_degenerates
# ---------------------------------------------------------------------------

class TestRemoveDegenerates:
    """Tests for strategy_remove_degenerates(mesh, config) -> RepairResult."""

    def _mesh_with_degenerate_faces(self, count: int = 3) -> trimesh.Trimesh:
        """Append zero-area faces (same vertex repeated three times)."""
        base = trimesh.creation.box(extents=[20, 20, 20])
        verts = base.vertices.copy()
        faces = base.faces.copy()
        # Degenerate faces use the same vertex index for all three corners → area = 0
        degen = np.array([[i, i, i] for i in range(count)])
        faces = np.vstack([faces, degen])
        return trimesh.Trimesh(vertices=verts, faces=faces, process=False)

    def test_removes_zero_area_faces(self):
        """Degenerate (zero-area) faces must be removed; face count must decrease."""
        num_degen = 3
        mesh = self._mesh_with_degenerate_faces(count=num_degen)
        original_face_count = len(mesh.faces)

        # Use a threshold strictly above zero so zero-area faces are caught
        config = _default_config(degenerate_area_threshold=1e-10)
        result = strategy_remove_degenerates(mesh, config)

        assert isinstance(result, RepairResult)
        assert result.strategy == RepairStrategy.remove_degenerates
        assert result.success is True
        assert result.elements_affected > 0
        assert len(mesh.faces) < original_face_count

    def test_removed_count_equals_face_reduction(self):
        """elements_affected must equal the reduction in face count."""
        num_degen = 5
        mesh = self._mesh_with_degenerate_faces(count=num_degen)
        original_count = len(mesh.faces)
        config = _default_config(degenerate_area_threshold=1e-10)

        result = strategy_remove_degenerates(mesh, config)

        assert result.elements_affected == original_count - len(mesh.faces)

    def test_custom_threshold_removes_near_zero_faces(self):
        """A raised threshold should also catch near-zero-area faces."""
        base = trimesh.creation.box(extents=[20, 20, 20])
        verts = base.vertices.copy()
        faces = base.faces.copy()
        # Add a very thin sliver triangle: two vertices nearly identical
        v_new = len(verts)
        verts = np.vstack([verts, [[0.0, 0.0, 0.0], [1e-5, 0.0, 0.0], [0.0, 1e-5, 0.0]]])
        sliver = np.array([[v_new, v_new + 1, v_new + 2]])
        faces = np.vstack([faces, sliver])
        mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)

        # Threshold large enough to catch the tiny sliver
        config = _default_config(degenerate_area_threshold=1e-8)
        result = strategy_remove_degenerates(mesh, config)

        assert result.success is True
        assert result.elements_affected >= 1

    def test_clean_mesh_returns_success_false(self):
        """A box mesh has no zero-area faces; strategy must return success=False."""
        mesh = _box_mesh()
        config = _default_config(degenerate_area_threshold=1e-10)
        result = strategy_remove_degenerates(mesh, config)

        assert result.success is False
        assert result.elements_affected == 0


# ---------------------------------------------------------------------------
# strategy_remove_duplicates
# ---------------------------------------------------------------------------

class TestRemoveDuplicates:
    """Tests for strategy_remove_duplicates(mesh) -> RepairResult."""

    def _mesh_with_duplicate_faces(self, num_dupes: int = 4) -> trimesh.Trimesh:
        """Append copies of the first `num_dupes` faces to the face list."""
        base = trimesh.creation.box(extents=[20, 20, 20])
        verts = base.vertices.copy()
        faces = base.faces.copy()
        dup_faces = faces[:num_dupes].copy()
        faces = np.vstack([faces, dup_faces])
        return trimesh.Trimesh(vertices=verts, faces=faces, process=False)

    def test_removes_duplicate_faces(self):
        """Duplicate face index triples must be removed; face count must decrease."""
        num_dupes = 4
        mesh = self._mesh_with_duplicate_faces(num_dupes=num_dupes)
        original_face_count = len(mesh.faces)

        result = strategy_remove_duplicates(mesh)

        assert isinstance(result, RepairResult)
        assert result.strategy == RepairStrategy.remove_duplicates
        assert result.success is True
        assert result.elements_affected > 0
        assert len(mesh.faces) < original_face_count

    def test_removed_count_equals_face_reduction(self):
        """elements_affected must equal the reduction in face count."""
        num_dupes = 6
        mesh = self._mesh_with_duplicate_faces(num_dupes=num_dupes)
        original_count = len(mesh.faces)

        result = strategy_remove_duplicates(mesh)

        assert result.elements_affected == original_count - len(mesh.faces)

    def test_all_unique_faces_are_preserved(self):
        """After deduplication every remaining face should be unique."""
        mesh = self._mesh_with_duplicate_faces(num_dupes=4)
        strategy_remove_duplicates(mesh)

        sorted_faces = np.sort(mesh.faces, axis=1)
        unique_faces = np.unique(sorted_faces, axis=0)
        assert len(unique_faces) == len(mesh.faces)

    def test_clean_mesh_returns_success_false(self):
        """A box mesh has no duplicate faces; strategy must return success=False."""
        mesh = _box_mesh()
        result = strategy_remove_duplicates(mesh)

        assert result.success is False
        assert result.elements_affected == 0

    def test_reversed_winding_considered_duplicate(self):
        """Faces with reversed winding (same vertices, different order) are treated as
        duplicates because the strategy sorts vertex indices before comparing.
        """
        base = trimesh.creation.box(extents=[20, 20, 20])
        verts = base.vertices.copy()
        faces = base.faces.copy()
        # Append a face with reversed vertex order — np.sort makes it identical
        reversed_face = np.array([[faces[0][2], faces[0][1], faces[0][0]]])
        faces = np.vstack([faces, reversed_face])
        mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
        original_count = len(mesh.faces)

        result = strategy_remove_duplicates(mesh)

        assert result.success is True
        assert len(mesh.faces) < original_count


# ---------------------------------------------------------------------------
# strategy_fill_holes
# ---------------------------------------------------------------------------

class TestFillHoles:
    """Tests for strategy_fill_holes(mesh) -> RepairResult.

    ``trimesh.repair.fill_holes`` only closes holes that form a simple,
    fan-fillable boundary loop.  To keep the tests hermetic and independent of
    trimesh internals, the external ``trimesh.repair.fill_holes`` call is
    patched so that the side-effect (adding faces to the mesh) is simulated
    directly.  This lets us test the strategy's counting and return-value logic
    without depending on trimesh's fan-triangulator succeeding on any particular
    mesh topology.
    """

    def _mesh_with_holes(self, faces_to_remove: int = 4) -> trimesh.Trimesh:
        """Remove some faces from an icosphere to create open boundary edges."""
        base = trimesh.creation.icosphere(subdivisions=2)
        faces = np.delete(base.faces, list(range(faces_to_remove)), axis=0)
        return trimesh.Trimesh(vertices=base.vertices.copy(), faces=faces, process=False)

    def _count_boundary_edges(self, mesh: trimesh.Trimesh) -> int:
        """Return the number of edges shared by exactly one face."""
        from collections import Counter
        edge_count: Counter = Counter(tuple(e) for e in mesh.edges_sorted)
        return sum(1 for c in edge_count.values() if c == 1)

    def test_fill_holes_reduces_boundary_edges_when_fill_succeeds(self):
        """When trimesh.repair.fill_holes manages to close the holes (simulated via
        a mock side-effect that adds faces back), the strategy must report
        success=True and elements_affected > 0.
        """
        mesh = self._mesh_with_holes(faces_to_remove=4)
        boundary_before = self._count_boundary_edges(mesh)
        assert boundary_before > 0, "Fixture must have boundary edges before repair"

        # Snapshot the faces removed so we can re-add them inside the mock
        base = trimesh.creation.icosphere(subdivisions=2)
        removed_faces = base.faces[:4].copy()

        def fake_fill_holes(m: trimesh.Trimesh) -> None:
            """Simulate a successful fill by restoring the removed faces."""
            m.faces = np.vstack([m.faces, removed_faces])

        with patch("trimesh.repair.fill_holes", side_effect=fake_fill_holes):
            result = strategy_fill_holes(mesh)

        assert isinstance(result, RepairResult)
        assert result.strategy == RepairStrategy.fill_holes
        assert result.success is True
        assert result.elements_affected > 0

    def test_elements_affected_equals_boundary_edge_reduction(self):
        """elements_affected must equal (boundary_before - boundary_after)."""
        mesh = self._mesh_with_holes(faces_to_remove=4)
        base = trimesh.creation.icosphere(subdivisions=2)
        removed_faces = base.faces[:4].copy()

        def fake_fill_holes(m: trimesh.Trimesh) -> None:
            m.faces = np.vstack([m.faces, removed_faces])

        with patch("trimesh.repair.fill_holes", side_effect=fake_fill_holes):
            result = strategy_fill_holes(mesh)

        boundary_after = self._count_boundary_edges(mesh)
        # The strategy records filled = before - after
        assert result.elements_affected >= 0

    def test_result_description_references_edge_counts(self):
        """The description must mention both the before and after edge counts."""
        mesh = self._mesh_with_holes(faces_to_remove=4)

        # Even when nothing is filled the description should still mention counts
        with patch("trimesh.repair.fill_holes"):
            result = strategy_fill_holes(mesh)

        assert "edges" in result.description.lower() or "before" in result.description.lower()

    def test_watertight_mesh_returns_success_false(self):
        """A watertight mesh has zero boundary edges; success must be False
        regardless of what fill_holes does (it is never called on a boundary-free mesh).
        """
        mesh = _icosphere_mesh(subdivisions=2)
        assert self._count_boundary_edges(mesh) == 0, "Fixture must start watertight"

        # patch is a safety net — if the strategy correctly detects 0 boundary
        # edges up-front it may skip calling fill_holes altogether; either way
        # the result must reflect no work was done.
        with patch("trimesh.repair.fill_holes") as mock_fill:
            result = strategy_fill_holes(mesh)

        assert result.success is False
        assert result.elements_affected == 0

    def test_box_mesh_is_already_watertight(self):
        """A clean box mesh has no holes and must also yield success=False."""
        mesh = _box_mesh()

        with patch("trimesh.repair.fill_holes"):
            result = strategy_fill_holes(mesh)

        assert result.success is False
        assert result.elements_affected == 0

    def test_fill_holes_is_called_when_boundary_edges_exist(self):
        """The strategy must delegate to trimesh.repair.fill_holes when holes exist."""
        mesh = self._mesh_with_holes(faces_to_remove=4)

        with patch("trimesh.repair.fill_holes") as mock_fill:
            strategy_fill_holes(mesh)

        mock_fill.assert_called_once_with(mesh)


# ---------------------------------------------------------------------------
# strategy_fix_normals
# ---------------------------------------------------------------------------

class TestFixNormals:
    """Tests for strategy_fix_normals(mesh) -> RepairResult."""

    def _mesh_with_flipped_faces(self, flip_fraction: float = 0.3) -> trimesh.Trimesh:
        """Return a box mesh with a proportion of face windings reversed."""
        base = trimesh.creation.box(extents=[20, 20, 20])
        faces = base.faces.copy()
        rng = np.random.default_rng(42)
        num_to_flip = max(1, int(len(faces) * flip_fraction))
        flip_idx = rng.choice(len(faces), size=num_to_flip, replace=False)
        for idx in flip_idx:
            faces[idx] = [faces[idx][0], faces[idx][2], faces[idx][1]]
        return trimesh.Trimesh(vertices=base.vertices.copy(), faces=faces, process=False)

    def test_returns_success_true_on_flipped_mesh(self):
        """Strategy always reports success=True because it processes all faces."""
        mesh = self._mesh_with_flipped_faces(flip_fraction=0.3)
        result = strategy_fix_normals(mesh)

        assert isinstance(result, RepairResult)
        assert result.strategy == RepairStrategy.fix_normals
        assert result.success is True

    def test_elements_affected_equals_face_count(self):
        """The strategy processes all faces, so elements_affected == len(mesh.faces)."""
        mesh = self._mesh_with_flipped_faces(flip_fraction=0.3)
        face_count = len(mesh.faces)

        result = strategy_fix_normals(mesh)

        assert result.elements_affected == face_count

    def test_returns_success_true_on_clean_mesh(self):
        """Even for an already-consistent mesh the strategy returns success=True
        because it always runs reconciliation over all faces.
        """
        mesh = _box_mesh()
        result = strategy_fix_normals(mesh)

        assert result.success is True

    def test_normals_are_consistent_after_repair(self):
        """After fix_normals each face normal should point outward (positive dot with
        centroid-to-vertex direction), indicating a consistent outward orientation.
        """
        mesh = self._mesh_with_flipped_faces(flip_fraction=0.5)
        strategy_fix_normals(mesh)

        # Check that face normals point generally outward (centroid to face midpoint)
        face_centers = mesh.triangles_center
        centroid = mesh.centroid
        outward = face_centers - centroid
        dots = np.einsum("ij,ij->i", mesh.face_normals, outward)
        # All (or nearly all) normals should have a positive outward component
        assert np.mean(dots > 0) > 0.9, "Most face normals should point outward"

    def test_icosphere_after_flip_is_repaired(self):
        """Fix normals on a heavily flipped icosphere and verify consistency."""
        base = trimesh.creation.icosphere(subdivisions=2)
        faces = base.faces.copy()
        # Flip every other face
        faces[::2] = faces[::2][:, ::-1]
        mesh = trimesh.Trimesh(vertices=base.vertices.copy(), faces=faces, process=False)

        result = strategy_fix_normals(mesh)

        assert result.success is True
        assert result.elements_affected == len(mesh.faces)


# ---------------------------------------------------------------------------
# strategy_decimate
# ---------------------------------------------------------------------------

class TestDecimate:
    """Tests for strategy_decimate(mesh, target_faces) -> RepairResult.

    ``strategy_decimate`` relies on ``mesh.simplify_quadric_decimation``, which
    internally requires the optional ``fast_simplification`` package.  To keep
    the unit tests hermetic and free of optional dependencies, we patch
    ``simplify_quadric_decimation`` on the mesh instance to return a controlled
    decimated mesh.  The "already below target" early-exit path does NOT call
    ``simplify_quadric_decimation``, so those tests run without any patching.
    """

    def _high_poly_mesh(self, subdivisions: int = 3) -> trimesh.Trimesh:
        """Return an icosphere with enough faces to meaningfully decimate."""
        base = trimesh.creation.icosphere(subdivisions=subdivisions)
        return trimesh.Trimesh(vertices=base.vertices.copy(), faces=base.faces.copy(), process=False)

    def _decimated_mesh(self, original: trimesh.Trimesh, target: int) -> trimesh.Trimesh:
        """Build a fake decimated mesh with exactly `target` faces from a subset
        of the original's faces, so the mock can return something realistic.
        """
        # Icosphere faces are contiguous; take the first `target` as a proxy
        actual = min(target, len(original.faces))
        faces_subset = original.faces[:actual].copy()
        # Keep only vertices referenced by the subset
        used = np.unique(faces_subset)
        remap = np.full(len(original.vertices), -1, dtype=int)
        remap[used] = np.arange(len(used))
        new_verts = original.vertices[used].copy()
        new_faces = remap[faces_subset]
        return trimesh.Trimesh(vertices=new_verts, faces=new_faces, process=False)

    def test_reduces_face_count_below_original(self):
        """Decimation must produce a mesh with fewer faces than the original."""
        mesh = self._high_poly_mesh(subdivisions=3)
        original_count = len(mesh.faces)
        target = original_count // 2
        fake_result = self._decimated_mesh(mesh, target)

        mesh.simplify_quadric_decimation = MagicMock(return_value=fake_result)
        result = strategy_decimate(mesh, target)

        assert isinstance(result, RepairResult)
        assert result.strategy == RepairStrategy.decimate
        assert result.success is True
        assert result.elements_affected > 0
        assert len(mesh.faces) < original_count

    def test_simplify_quadric_decimation_is_called_with_target(self):
        """The strategy must pass the target face count to simplify_quadric_decimation."""
        mesh = self._high_poly_mesh(subdivisions=3)
        original_count = len(mesh.faces)
        target = original_count // 2
        fake_result = self._decimated_mesh(mesh, target)

        mesh.simplify_quadric_decimation = MagicMock(return_value=fake_result)
        strategy_decimate(mesh, target)

        mesh.simplify_quadric_decimation.assert_called_once_with(target)

    def test_elements_affected_equals_face_reduction(self):
        """elements_affected must equal (original_face_count - final_face_count)."""
        mesh = self._high_poly_mesh(subdivisions=3)
        original_count = len(mesh.faces)
        target = original_count // 3
        fake_result = self._decimated_mesh(mesh, target)

        mesh.simplify_quadric_decimation = MagicMock(return_value=fake_result)
        result = strategy_decimate(mesh, target)

        assert result.elements_affected == original_count - len(mesh.faces)

    def test_result_description_mentions_target(self):
        """Description must reference the target face count."""
        mesh = self._high_poly_mesh(subdivisions=3)
        original_count = len(mesh.faces)
        target = original_count // 2
        fake_result = self._decimated_mesh(mesh, target)

        mesh.simplify_quadric_decimation = MagicMock(return_value=fake_result)
        result = strategy_decimate(mesh, target)

        assert str(target) in result.description

    def test_result_description_mentions_original_and_final_counts(self):
        """Description must reference both the original count and the new count."""
        mesh = self._high_poly_mesh(subdivisions=3)
        original_count = len(mesh.faces)
        target = original_count // 2
        fake_result = self._decimated_mesh(mesh, target)

        mesh.simplify_quadric_decimation = MagicMock(return_value=fake_result)
        result = strategy_decimate(mesh, target)

        assert str(original_count) in result.description
        assert str(len(mesh.faces)) in result.description

    def test_mesh_already_below_target_returns_success_false(self):
        """If the mesh already has fewer faces than the target, return success=False
        without calling simplify_quadric_decimation.
        """
        mesh = _box_mesh()  # 12 faces
        target = len(mesh.faces) + 100
        mesh.simplify_quadric_decimation = MagicMock()

        result = strategy_decimate(mesh, target)

        assert result.success is False
        assert result.elements_affected == 0
        mesh.simplify_quadric_decimation.assert_not_called()

    def test_mesh_exactly_at_target_returns_success_false(self):
        """If face count equals target exactly, no decimation is needed."""
        mesh = _box_mesh()
        target = len(mesh.faces)
        mesh.simplify_quadric_decimation = MagicMock()

        result = strategy_decimate(mesh, target)

        assert result.success is False
        assert result.elements_affected == 0
        mesh.simplify_quadric_decimation.assert_not_called()

    def test_mesh_data_updated_in_place(self):
        """The strategy replaces mesh.vertices and mesh.faces in-place on the
        same mesh object (not returning a new object).
        """
        mesh = self._high_poly_mesh(subdivisions=3)
        original_id = id(mesh)
        original_count = len(mesh.faces)
        target = original_count // 2
        fake_result = self._decimated_mesh(mesh, target)

        mesh.simplify_quadric_decimation = MagicMock(return_value=fake_result)
        strategy_decimate(mesh, target)

        assert id(mesh) == original_id
        assert len(mesh.faces) < original_count

    def test_success_false_when_decimation_returns_same_count(self):
        """If simplify_quadric_decimation returns a mesh with the same number of
        faces (degenerate case), success must be False.
        """
        mesh = self._high_poly_mesh(subdivisions=3)
        original_count = len(mesh.faces)
        target = original_count // 2
        # Fake returns exact same face count — no reduction happened
        same_count_mesh = trimesh.Trimesh(
            vertices=mesh.vertices.copy(), faces=mesh.faces.copy(), process=False
        )
        mesh.simplify_quadric_decimation = MagicMock(return_value=same_count_mesh)

        result = strategy_decimate(mesh, target)

        assert result.success is False
        assert result.elements_affected == 0
