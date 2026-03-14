"""Integration tests for the full repair pipeline (repair_mesh public API).

These tests exercise the end-to-end path from a raw mesh file on disk through
analysis, the ordered repair strategy pipeline, and final export — without
requiring OpenSCAD or any rendering dependency.

All tests pass RepairConfig(render_previews=False) so that the pipeline never
attempts to invoke the renderer, keeping the suite hermetic.

Design notes
------------
- ``mesh_with_holes`` reliably triggers the repair pipeline because removing 4
  faces from an icosphere creates many critical boundary-edge defects, pushing
  the health score well below the 0.8 print-ready threshold.
- ``mesh_self_intersecting`` in conftest is two *separate* shells (two
  overlapping boxes that trimesh splits into independent components on load).
  Each shell is individually clean, so per-shell analysis never flags
  self-intersections and the mesh is classified print-ready immediately.
  For the "unfixable defects" scenario we therefore build a single-body
  self-intersecting mesh directly in the test, then write it to tmp_path so
  the fixture pattern is preserved.
- Classification thresholds: score >= 0.8 → print_ready.  A mesh with many
  boundary-edge defects easily falls into "repairable" but hole-filling may
  leave residual inconsistencies, so we verify *improvement* rather than
  a specific final class.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest
import trimesh

from print3d_skill.models.analysis import DefectType, MeshHealthClassification
from print3d_skill.models.repair import RepairConfig, RepairSummary
from print3d_skill.repair import repair_mesh


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _no_render_config(**kwargs) -> RepairConfig:
    """Return a RepairConfig with previews disabled plus any extra overrides."""
    return RepairConfig(render_previews=False, **kwargs)


def _make_heavily_non_manifold_stl(path: Path) -> None:
    """Write a heavily non-manifold mesh STL to *path*.

    Adds many extra triangles that all share the same base edge (vertices 0-1
    of a box), creating a large number of non-manifold edges.  This pushes the
    health score below the 0.8 print-ready threshold (requires >= 3 critical
    defect elements: penalty = 3 * 0.1 = 0.3 → score = 0.7 → repairable),
    ensuring the repair pipeline actually runs.

    Non-manifold edges are not addressed by any current repair strategy, so
    they survive as remaining_defects after the pipeline completes.

    The mesh remains a single body (no shell-splitting) because all extra
    triangles share vertices with the original box.
    """
    mesh = trimesh.creation.box(extents=[20, 20, 20])
    verts = mesh.vertices.copy()
    faces = mesh.faces.copy()

    # Add 5 extra vertices offset from the mesh
    extra_verts = np.array([
        [0.0, 0.0, 25.0],
        [5.0, 0.0, 25.0],
        [10.0, 0.0, 25.0],
        [15.0, 0.0, 25.0],
        [20.0, 0.0, 25.0],
    ])
    first_extra = len(verts)
    verts = np.vstack([verts, extra_verts])

    # Each extra triangle shares edge (faces[0][0], faces[0][1]) with the
    # first face of the box, making that edge non-manifold (3+ faces share it).
    v0, v1 = int(faces[0][0]), int(faces[0][1])
    extra_faces = np.array([
        [v0, v1, first_extra + 0],
        [v0, v1, first_extra + 1],
        [v0, v1, first_extra + 2],
        [v0, v1, first_extra + 3],
        [v0, v1, first_extra + 4],
    ])
    faces = np.vstack([faces, extra_faces])

    non_manifold_mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    non_manifold_mesh.export(str(path), file_type="stl")


# ---------------------------------------------------------------------------
# Scenario 1 — Defective mesh produces a repaired file and populated summary
# ---------------------------------------------------------------------------

class TestDefectiveMeshProducesRepairedOutput:
    """A mesh with holes must yield exported files on disk and a summary that
    reflects both the defects that were found and the repair work performed."""

    def test_summary_is_repair_summary_instance(
        self, mesh_with_holes: Path, tmp_path: Path
    ):
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(mesh_with_holes), config=config)

        assert isinstance(summary, RepairSummary)

    def test_summary_mesh_path_matches_input(
        self, mesh_with_holes: Path, tmp_path: Path
    ):
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(mesh_with_holes), config=config)

        assert summary.mesh_path == str(mesh_with_holes.resolve())

    def test_initial_analysis_populated(
        self, mesh_with_holes: Path, tmp_path: Path
    ):
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(mesh_with_holes), config=config)

        assert summary.initial_analysis is not None
        assert summary.initial_analysis.face_count > 0
        assert summary.initial_analysis.vertex_count > 0

    def test_initial_analysis_detected_defects(
        self, mesh_with_holes: Path, tmp_path: Path
    ):
        # The holed sphere must be classified as defective before repair.
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(mesh_with_holes), config=config)

        assert summary.total_defects_found > 0
        initial_defect_types = {d.defect_type for d in summary.initial_analysis.defects}
        assert DefectType.boundary_edges in initial_defect_types

    def test_final_analysis_populated(
        self, mesh_with_holes: Path, tmp_path: Path
    ):
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(mesh_with_holes), config=config)

        assert summary.final_analysis is not None
        assert summary.final_analysis.face_count > 0

    def test_repairs_list_is_non_empty(
        self, mesh_with_holes: Path, tmp_path: Path
    ):
        # The pipeline must have executed at least one repair strategy.
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(mesh_with_holes), config=config)

        assert len(summary.repairs) > 0

    def test_export_paths_are_populated(
        self, mesh_with_holes: Path, tmp_path: Path
    ):
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(mesh_with_holes), config=config)

        assert len(summary.export_paths) > 0

    def test_exported_stl_file_exists_on_disk(
        self, mesh_with_holes: Path, tmp_path: Path
    ):
        # Default export_formats includes "stl".
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(mesh_with_holes), config=config)

        assert "stl" in summary.export_paths
        assert os.path.exists(summary.export_paths["stl"])

    def test_exported_file_has_non_zero_size(
        self, mesh_with_holes: Path, tmp_path: Path
    ):
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(mesh_with_holes), config=config)

        stl_path = summary.export_paths["stl"]
        assert os.path.getsize(stl_path) > 0

    def test_total_defects_fixed_is_non_negative(
        self, mesh_with_holes: Path, tmp_path: Path
    ):
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(mesh_with_holes), config=config)

        assert summary.total_defects_fixed >= 0

    def test_health_score_does_not_decrease_after_repair(
        self, mesh_with_holes: Path, tmp_path: Path
    ):
        # The pipeline must not worsen the mesh: final health score >= initial.
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(mesh_with_holes), config=config)

        assert summary.final_analysis.health_score >= summary.initial_analysis.health_score

    def test_all_expected_pipeline_steps_are_present_in_repairs(
        self, mesh_with_holes: Path, tmp_path: Path
    ):
        # The ordered pipeline always runs all 5 core strategies regardless of
        # whether each one individually reports success.  Every strategy name
        # must appear exactly once in the repairs list.
        from print3d_skill.models.repair import RepairStrategy

        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(mesh_with_holes), config=config)

        strategy_names = {r.strategy for r in summary.repairs}
        expected = {
            RepairStrategy.merge_vertices,
            RepairStrategy.remove_degenerates,
            RepairStrategy.remove_duplicates,
            RepairStrategy.fill_holes,
            RepairStrategy.fix_normals,
        }
        assert expected.issubset(strategy_names), (
            f"Missing strategies: {expected - strategy_names}"
        )


# ---------------------------------------------------------------------------
# Scenario 2 — Unfixable defects are listed in remaining_defects
# ---------------------------------------------------------------------------

class TestUnfixableDefectsListedInRemaining:
    """Non-manifold edges cannot be resolved by any current repair strategy
    (merge_vertices, fill_holes, fix_normals, remove_degenerates,
    remove_duplicates).  The summary must therefore include them in
    remaining_defects so callers know further manual intervention is needed.

    Implementation note: the conftest ``mesh_self_intersecting`` fixture
    produces *two disjoint shells* (two clean boxes loaded as independent
    components by trimesh).  Per-shell analysis never flags self-intersections
    on an individually clean shell, so the whole mesh is classified
    print-ready and the pipeline short-circuits without running.

    To reliably exercise the "unfixable defects remain" path we instead
    construct a heavily non-manifold single-body mesh via the module-level
    helper ``_make_heavily_non_manifold_stl``.  Five extra triangles all
    share the same base edge, creating many non-manifold edge detections
    (critical severity).  The resulting health score falls below 0.8, the
    repair pipeline runs in full, and non_manifold_edges survive as
    remaining defects because no strategy removes them.
    """

    @pytest.fixture()
    def heavily_non_manifold_stl(self, tmp_path: Path) -> Path:
        """Write a heavily non-manifold mesh STL and return its Path."""
        path = tmp_path / "heavily_non_manifold.stl"
        _make_heavily_non_manifold_stl(path)
        return path

    def test_summary_returned_for_non_manifold_mesh(
        self, heavily_non_manifold_stl: Path, tmp_path: Path
    ):
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(heavily_non_manifold_stl), config=config)

        assert isinstance(summary, RepairSummary)

    def test_initial_analysis_detected_non_manifold_edges(
        self, heavily_non_manifold_stl: Path, tmp_path: Path
    ):
        # Five extra triangles sharing the same base edge produce many
        # non-manifold-edge detections on a single-shell mesh.
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(heavily_non_manifold_stl), config=config)

        initial_defect_types = {d.defect_type for d in summary.initial_analysis.defects}
        assert DefectType.non_manifold_edges in initial_defect_types

    def test_remaining_defects_is_not_empty(
        self, heavily_non_manifold_stl: Path, tmp_path: Path
    ):
        # Non-manifold edges survive the pipeline, so remaining_defects must
        # contain at least one entry after repair completes.
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(heavily_non_manifold_stl), config=config)

        assert len(summary.remaining_defects) > 0

    def test_non_manifold_edges_still_present_after_repair(
        self, heavily_non_manifold_stl: Path, tmp_path: Path
    ):
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(heavily_non_manifold_stl), config=config)

        remaining_types = {d.defect_type for d in summary.remaining_defects}
        assert DefectType.non_manifold_edges in remaining_types

    def test_total_defects_fixed_does_not_exceed_found(
        self, heavily_non_manifold_stl: Path, tmp_path: Path
    ):
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(heavily_non_manifold_stl), config=config)

        assert summary.total_defects_fixed <= summary.total_defects_found

    def test_export_paths_still_populated_for_unfixable_mesh(
        self, heavily_non_manifold_stl: Path, tmp_path: Path
    ):
        # The pipeline exports the best-effort result even when defects remain.
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(heavily_non_manifold_stl), config=config)

        assert len(summary.export_paths) > 0
        for fmt, path in summary.export_paths.items():
            assert os.path.exists(path), (
                f"Expected export file to exist for format '{fmt}': {path}"
            )


# ---------------------------------------------------------------------------
# Scenario 3 — 3MF export format
# ---------------------------------------------------------------------------

class TestThreeMfExportFormat:
    """When export_formats=["3mf"] is specified, only a 3MF file should be
    produced and its path should be present in export_paths."""

    def test_3mf_key_present_in_export_paths(
        self, mesh_with_bad_normals: Path, tmp_path: Path
    ):
        config = _no_render_config(
            output_dir=str(tmp_path),
            export_formats=["3mf"],
        )
        summary = repair_mesh(str(mesh_with_bad_normals), config=config)

        assert "3mf" in summary.export_paths

    def test_3mf_file_exists_on_disk(
        self, mesh_with_bad_normals: Path, tmp_path: Path
    ):
        config = _no_render_config(
            output_dir=str(tmp_path),
            export_formats=["3mf"],
        )
        summary = repair_mesh(str(mesh_with_bad_normals), config=config)

        assert os.path.exists(summary.export_paths["3mf"])

    def test_3mf_file_has_non_zero_size(
        self, mesh_with_bad_normals: Path, tmp_path: Path
    ):
        config = _no_render_config(
            output_dir=str(tmp_path),
            export_formats=["3mf"],
        )
        summary = repair_mesh(str(mesh_with_bad_normals), config=config)

        assert os.path.getsize(summary.export_paths["3mf"]) > 0

    def test_only_3mf_exported_when_format_restricted(
        self, mesh_with_bad_normals: Path, tmp_path: Path
    ):
        # With export_formats=["3mf"], the STL key must NOT be present.
        config = _no_render_config(
            output_dir=str(tmp_path),
            export_formats=["3mf"],
        )
        summary = repair_mesh(str(mesh_with_bad_normals), config=config)

        assert "stl" not in summary.export_paths
        assert list(summary.export_paths.keys()) == ["3mf"]

    def test_3mf_path_ends_with_correct_extension(
        self, mesh_with_bad_normals: Path, tmp_path: Path
    ):
        config = _no_render_config(
            output_dir=str(tmp_path),
            export_formats=["3mf"],
        )
        summary = repair_mesh(str(mesh_with_bad_normals), config=config)

        assert summary.export_paths["3mf"].endswith(".3mf")

    def test_3mf_export_for_multiple_formats_includes_stl_too(
        self, mesh_with_bad_normals: Path, tmp_path: Path
    ):
        # Confirm the default config produces both stl and 3mf side-by-side.
        config = _no_render_config(
            output_dir=str(tmp_path),
            export_formats=["stl", "3mf"],
        )
        summary = repair_mesh(str(mesh_with_bad_normals), config=config)

        assert "stl" in summary.export_paths
        assert "3mf" in summary.export_paths
        assert os.path.exists(summary.export_paths["stl"])
        assert os.path.exists(summary.export_paths["3mf"])


# ---------------------------------------------------------------------------
# Scenario 4 — Before/after previews skipped when render_previews=False
# ---------------------------------------------------------------------------

class TestPreviewsSkippedWhenRenderingDisabled:
    """With RepairConfig(render_previews=False), no preview images should be
    generated.  Every RepairResult in the repairs list must have both
    before_preview_path and after_preview_path set to None."""

    def test_repairs_list_non_empty(
        self, mesh_with_holes: Path, tmp_path: Path
    ):
        # Sanity check: repairs were still executed even without previews.
        config = RepairConfig(render_previews=False, output_dir=str(tmp_path))
        summary = repair_mesh(str(mesh_with_holes), config=config)

        assert len(summary.repairs) > 0

    def test_all_before_preview_paths_are_none(
        self, mesh_with_holes: Path, tmp_path: Path
    ):
        config = RepairConfig(render_previews=False, output_dir=str(tmp_path))
        summary = repair_mesh(str(mesh_with_holes), config=config)

        for result in summary.repairs:
            assert result.before_preview_path is None, (
                f"Strategy '{result.strategy}' has a non-None before_preview_path "
                f"despite render_previews=False: {result.before_preview_path}"
            )

    def test_all_after_preview_paths_are_none(
        self, mesh_with_holes: Path, tmp_path: Path
    ):
        config = RepairConfig(render_previews=False, output_dir=str(tmp_path))
        summary = repair_mesh(str(mesh_with_holes), config=config)

        for result in summary.repairs:
            assert result.after_preview_path is None, (
                f"Strategy '{result.strategy}' has a non-None after_preview_path "
                f"despite render_previews=False: {result.after_preview_path}"
            )

    def test_previews_skipped_for_bad_normals_mesh(
        self, mesh_with_bad_normals: Path, tmp_path: Path
    ):
        # Run with a different fixture to confirm the behaviour is not fixture-
        # specific.
        config = RepairConfig(render_previews=False, output_dir=str(tmp_path))
        summary = repair_mesh(str(mesh_with_bad_normals), config=config)

        for result in summary.repairs:
            assert result.before_preview_path is None
            assert result.after_preview_path is None

    def test_previews_skipped_for_self_intersecting_mesh(
        self, mesh_self_intersecting: Path, tmp_path: Path
    ):
        config = RepairConfig(render_previews=False, output_dir=str(tmp_path))
        summary = repair_mesh(str(mesh_self_intersecting), config=config)

        for result in summary.repairs:
            assert result.before_preview_path is None
            assert result.after_preview_path is None

    def test_pipeline_still_exports_files_without_previews(
        self, mesh_with_holes: Path, tmp_path: Path
    ):
        # Disabling previews must not prevent export.
        config = RepairConfig(render_previews=False, output_dir=str(tmp_path))
        summary = repair_mesh(str(mesh_with_holes), config=config)

        assert len(summary.export_paths) > 0
        for path in summary.export_paths.values():
            assert os.path.exists(path)


# ---------------------------------------------------------------------------
# Scenario 5 — Clean (print-ready) mesh is returned idempotently
# ---------------------------------------------------------------------------

class TestCleanMeshIsIdempotent:
    """A mesh already classified as print_ready must be returned immediately
    with an empty repairs list and no export files (no unnecessary work done)."""

    def test_returns_repair_summary(self, clean_mesh: Path, tmp_path: Path):
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(clean_mesh), config=config)

        assert isinstance(summary, RepairSummary)

    def test_repairs_list_is_empty_for_clean_mesh(
        self, clean_mesh: Path, tmp_path: Path
    ):
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(clean_mesh), config=config)

        assert summary.repairs == []

    def test_total_defects_found_is_zero_for_clean_mesh(
        self, clean_mesh: Path, tmp_path: Path
    ):
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(clean_mesh), config=config)

        assert summary.total_defects_found == 0

    def test_remaining_defects_empty_for_clean_mesh(
        self, clean_mesh: Path, tmp_path: Path
    ):
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(clean_mesh), config=config)

        assert summary.remaining_defects == []

    def test_classification_unchanged_for_clean_mesh(
        self, clean_mesh: Path, tmp_path: Path
    ):
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(clean_mesh), config=config)

        assert summary.classification_changed is False

    def test_initial_and_final_classifications_are_print_ready(
        self, clean_mesh: Path, tmp_path: Path
    ):
        config = _no_render_config(output_dir=str(tmp_path))
        summary = repair_mesh(str(clean_mesh), config=config)

        assert summary.initial_analysis.classification == MeshHealthClassification.print_ready
        assert summary.final_analysis.classification == MeshHealthClassification.print_ready


# ---------------------------------------------------------------------------
# Scenario 6 — Error handling
# ---------------------------------------------------------------------------

class TestRepairErrorHandling:
    """Verify that repair_mesh raises the correct exceptions for bad inputs."""

    def test_raises_file_not_found_for_missing_path(self, tmp_path: Path):
        config = _no_render_config(output_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            repair_mesh("/nonexistent/path/model.stl", config=config)

    def test_raises_unsupported_format_for_step_file(self, tmp_path: Path):
        from print3d_skill.exceptions import UnsupportedFormatError

        step_file = tmp_path / "model.step"
        step_file.write_text("ISO-10303-21; fake step content")

        config = _no_render_config(output_dir=str(tmp_path))
        with pytest.raises(UnsupportedFormatError):
            repair_mesh(str(step_file), config=config)
