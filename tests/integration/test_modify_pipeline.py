"""Integration tests for the modify pipeline (modify_mesh public API).

These tests exercise the end-to-end path for each modify operation:
boolean, scale, combine, split, and operation chaining.

All tests use programmatically generated fixtures from conftest.py
(no binary fixtures checked into the repo) and manifold3d for CSG.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest
import trimesh

from print3d_skill import modify_mesh
from print3d_skill.models.modify import ModifyOperation, ModifyResult


# ---------------------------------------------------------------------------
# T034 -- Boolean pipeline
# ---------------------------------------------------------------------------


class TestBooleanPipeline:
    """Load cube_stl, boolean-difference a cylinder primitive (6mm diameter,
    30mm height at center), and verify output integrity."""

    def test_output_file_exists_and_is_watertight(
        self, cube_stl: Path, tmp_path: Path
    ):
        output = str(tmp_path / "cube_bool.stl")
        result = modify_mesh(
            mesh_path=str(cube_stl),
            operation="boolean",
            output_path=output,
            boolean_type="difference",
            primitive_type="cylinder",
            primitive_dimensions={"diameter": 6.0, "height": 30.0},
            primitive_position=(0.0, 0.0, 0.0),
        )

        assert os.path.exists(result.output_mesh_paths[0])
        loaded = trimesh.load(result.output_mesh_paths[0], force="mesh")
        assert loaded.is_watertight

    def test_volume_decreased_vs_original(
        self, cube_stl: Path, tmp_path: Path
    ):
        output = str(tmp_path / "cube_bool_vol.stl")
        result = modify_mesh(
            mesh_path=str(cube_stl),
            operation="boolean",
            output_path=output,
            boolean_type="difference",
            primitive_type="cylinder",
            primitive_dimensions={"diameter": 6.0, "height": 30.0},
            primitive_position=(0.0, 0.0, 0.0),
        )

        original = trimesh.load(str(cube_stl), force="mesh")
        modified = trimesh.load(result.output_mesh_paths[0], force="mesh")
        assert modified.volume < original.volume

    def test_before_after_preview_pngs_exist(
        self, cube_stl: Path, tmp_path: Path
    ):
        output = str(tmp_path / "cube_bool_prev.stl")
        result = modify_mesh(
            mesh_path=str(cube_stl),
            operation="boolean",
            output_path=output,
            boolean_type="difference",
            primitive_type="cylinder",
            primitive_dimensions={"diameter": 6.0, "height": 30.0},
            primitive_position=(0.0, 0.0, 0.0),
        )

        assert result.before_preview_path is not None
        assert os.path.exists(result.before_preview_path)
        assert len(result.after_preview_paths) > 0
        for p in result.after_preview_paths:
            assert os.path.exists(p)

    def test_analysis_report_populated(
        self, cube_stl: Path, tmp_path: Path
    ):
        output = str(tmp_path / "cube_bool_analysis.stl")
        result = modify_mesh(
            mesh_path=str(cube_stl),
            operation="boolean",
            output_path=output,
            boolean_type="difference",
            primitive_type="cylinder",
            primitive_dimensions={"diameter": 6.0, "height": 30.0},
            primitive_position=(0.0, 0.0, 0.0),
        )

        assert result.analysis_report is not None
        assert result.analysis_report.health_score > 0
        assert result.analysis_report.classification is not None
        assert result.analysis_report.face_count > 0

    def test_modify_result_has_correct_fields(
        self, cube_stl: Path, tmp_path: Path
    ):
        output = str(tmp_path / "cube_bool_fields.stl")
        result = modify_mesh(
            mesh_path=str(cube_stl),
            operation="boolean",
            output_path=output,
            boolean_type="difference",
            primitive_type="cylinder",
            primitive_dimensions={"diameter": 6.0, "height": 30.0},
            primitive_position=(0.0, 0.0, 0.0),
        )

        assert isinstance(result, ModifyResult)
        assert result.operation == ModifyOperation.BOOLEAN
        assert result.input_mesh_path == str(cube_stl.resolve())
        assert len(result.output_mesh_paths) == 1
        assert result.bbox_before is not None
        assert result.bbox_after is not None
        assert result.vertex_count_before > 0
        assert result.vertex_count_after > 0
        assert result.face_count_before > 0
        assert result.face_count_after > 0


# ---------------------------------------------------------------------------
# T035 -- Scale + feature detection
# ---------------------------------------------------------------------------


class TestScaleWithFeatureDetection:
    """Load mesh_with_screw_holes, scale uniformly by 150%, and verify
    bounding box dimensions and comparison previews."""

    def test_bounding_box_dimensions_are_150_percent(
        self, mesh_with_screw_holes: Path, tmp_path: Path
    ):
        output = str(tmp_path / "scaled_150.stl")
        result = modify_mesh(
            mesh_path=str(mesh_with_screw_holes),
            operation="scale",
            output_path=output,
            scale_mode="uniform",
            factor=1.5,
        )

        before_dims = result.bbox_before.dimensions
        after_dims = result.bbox_after.dimensions

        for i in range(3):
            expected = before_dims[i] * 1.5
            assert abs(after_dims[i] - expected) < 0.1, (
                f"Axis {i}: expected {expected:.2f}, got {after_dims[i]:.2f}"
            )

    def test_bbox_before_and_after_populated(
        self, mesh_with_screw_holes: Path, tmp_path: Path
    ):
        output = str(tmp_path / "scaled_bbox.stl")
        result = modify_mesh(
            mesh_path=str(mesh_with_screw_holes),
            operation="scale",
            output_path=output,
            scale_mode="uniform",
            factor=1.5,
        )

        assert result.bbox_before is not None
        assert result.bbox_after is not None
        # Before bbox should match original mesh dimensions
        assert all(d > 0 for d in result.bbox_before.dimensions)
        # After bbox should be larger (150% scale)
        assert all(d > 0 for d in result.bbox_after.dimensions)

    def test_comparison_previews_exist(
        self, mesh_with_screw_holes: Path, tmp_path: Path
    ):
        output = str(tmp_path / "scaled_previews.stl")
        result = modify_mesh(
            mesh_path=str(mesh_with_screw_holes),
            operation="scale",
            output_path=output,
            scale_mode="uniform",
            factor=1.5,
        )

        assert result.before_preview_path is not None
        assert os.path.exists(result.before_preview_path)
        assert len(result.after_preview_paths) > 0
        for p in result.after_preview_paths:
            assert os.path.exists(p)


# ---------------------------------------------------------------------------
# T036 -- Combine pipeline
# ---------------------------------------------------------------------------


class TestCombinePipeline:
    """Load cube_stl and second_box_stl, combine with alignment='top',
    and verify output integrity and positioning."""

    def test_single_output_mesh_produced(
        self, cube_stl: Path, second_box_stl: Path, tmp_path: Path
    ):
        output = str(tmp_path / "combined.stl")
        result = modify_mesh(
            mesh_path=str(cube_stl),
            operation="combine",
            output_path=output,
            other_mesh_paths=[str(second_box_stl)],
            alignment="top",
        )

        assert len(result.output_mesh_paths) == 1
        assert os.path.exists(result.output_mesh_paths[0])

    def test_output_is_watertight(
        self, cube_stl: Path, second_box_stl: Path, tmp_path: Path
    ):
        output = str(tmp_path / "combined_wt.stl")
        result = modify_mesh(
            mesh_path=str(cube_stl),
            operation="combine",
            output_path=output,
            other_mesh_paths=[str(second_box_stl)],
            alignment="top",
        )

        loaded = trimesh.load(result.output_mesh_paths[0], force="mesh")
        assert loaded.is_watertight

    def test_correct_positioning_top_alignment(
        self, cube_stl: Path, second_box_stl: Path, tmp_path: Path
    ):
        output = str(tmp_path / "combined_pos.stl")
        result = modify_mesh(
            mesh_path=str(cube_stl),
            operation="combine",
            output_path=output,
            other_mesh_paths=[str(second_box_stl)],
            alignment="top",
        )

        # With "top" alignment, the second box should be placed on top of the cube.
        # The cube is 20x20x20 (centered, so Z from -10 to +10).
        # The second box is 20x20x20, placed on top -> Z from +10 to +30.
        # Combined bbox Z-max should be greater than original.
        assert result.bbox_after.max_point[2] > result.bbox_before.max_point[2]

    def test_comparison_previews_exist(
        self, cube_stl: Path, second_box_stl: Path, tmp_path: Path
    ):
        output = str(tmp_path / "combined_prev.stl")
        result = modify_mesh(
            mesh_path=str(cube_stl),
            operation="combine",
            output_path=output,
            other_mesh_paths=[str(second_box_stl)],
            alignment="top",
        )

        assert result.before_preview_path is not None
        assert os.path.exists(result.before_preview_path)
        assert len(result.after_preview_paths) > 0
        for p in result.after_preview_paths:
            assert os.path.exists(p)


# ---------------------------------------------------------------------------
# T037 -- Split pipeline
# ---------------------------------------------------------------------------


class TestSplitPipeline:
    """Load tall_box_stl (40x40x100mm), split at Z=50mm with alignment
    features, and verify both parts."""

    def test_two_output_files_produced(
        self, tall_box_stl: Path, tmp_path: Path
    ):
        result = modify_mesh(
            mesh_path=str(tall_box_stl),
            operation="split",
            output_path=None,
            split_axis="z",
            split_offset_mm=50.0,
            add_alignment=True,
        )

        assert len(result.output_mesh_paths) == 2
        for p in result.output_mesh_paths:
            assert os.path.exists(p)

    def test_both_parts_are_watertight(
        self, tall_box_stl: Path, tmp_path: Path
    ):
        result = modify_mesh(
            mesh_path=str(tall_box_stl),
            operation="split",
            output_path=None,
            split_axis="z",
            split_offset_mm=50.0,
            add_alignment=True,
        )

        for p in result.output_mesh_paths:
            loaded = trimesh.load(p, force="mesh")
            assert loaded.is_watertight, f"Part {p} is not watertight"

    def test_combined_volume_within_5_percent_of_original(
        self, tall_box_stl: Path, tmp_path: Path
    ):
        result = modify_mesh(
            mesh_path=str(tall_box_stl),
            operation="split",
            output_path=None,
            split_axis="z",
            split_offset_mm=50.0,
            add_alignment=True,
        )

        original = trimesh.load(str(tall_box_stl), force="mesh")
        original_volume = original.volume

        combined_volume = 0.0
        for p in result.output_mesh_paths:
            part = trimesh.load(p, force="mesh")
            combined_volume += part.volume

        # Alignment features add/subtract material, so allow 5% tolerance
        ratio = combined_volume / original_volume
        assert 0.95 <= ratio <= 1.05, (
            f"Combined volume ratio {ratio:.3f} is outside 5% tolerance "
            f"(original={original_volume:.1f}, combined={combined_volume:.1f})"
        )

    def test_alignment_features_list_is_non_empty(
        self, tall_box_stl: Path, tmp_path: Path
    ):
        result = modify_mesh(
            mesh_path=str(tall_box_stl),
            operation="split",
            output_path=None,
            split_axis="z",
            split_offset_mm=50.0,
            add_alignment=True,
        )

        assert len(result.alignment_features) > 0

    def test_per_part_preview_paths_exist(
        self, tall_box_stl: Path, tmp_path: Path
    ):
        result = modify_mesh(
            mesh_path=str(tall_box_stl),
            operation="split",
            output_path=None,
            split_axis="z",
            split_offset_mm=50.0,
            add_alignment=True,
        )

        assert result.before_preview_path is not None
        assert os.path.exists(result.before_preview_path)
        # Split produces multiple after-previews (one per part)
        assert len(result.after_preview_paths) == len(result.output_mesh_paths)
        for p in result.after_preview_paths:
            assert os.path.exists(p)


# ---------------------------------------------------------------------------
# T038 -- Operation chaining
# ---------------------------------------------------------------------------


class TestOperationChaining:
    """Scale box_with_known_dims by 120%, then boolean-subtract a cylinder
    from the scaled output, verifying both operations are reflected."""

    def test_final_mesh_reflects_both_operations(
        self, box_with_known_dims: Path, tmp_path: Path
    ):
        # Step 1: Scale by 120%
        scaled_output = str(tmp_path / "chained_scaled.stl")
        scale_result = modify_mesh(
            mesh_path=str(box_with_known_dims),
            operation="scale",
            output_path=scaled_output,
            scale_mode="uniform",
            factor=1.2,
        )

        # Verify scaling was applied (original 40x30x20 -> 48x36x24)
        scaled_dims = scale_result.bbox_after.dimensions
        assert abs(scaled_dims[0] - 48.0) < 0.5
        assert abs(scaled_dims[1] - 36.0) < 0.5
        assert abs(scaled_dims[2] - 24.0) < 0.5

        # Step 2: Boolean subtract cylinder from scaled mesh
        bool_output = str(tmp_path / "chained_bool.stl")
        bool_result = modify_mesh(
            mesh_path=scale_result.output_mesh_paths[0],
            operation="boolean",
            output_path=bool_output,
            boolean_type="difference",
            primitive_type="cylinder",
            primitive_dimensions={"diameter": 6.0, "height": 30.0},
            primitive_position=(0.0, 0.0, 0.0),
        )

        # Final mesh should have smaller volume than scaled mesh
        scaled_mesh = trimesh.load(scaled_output, force="mesh")
        final_mesh = trimesh.load(bool_result.output_mesh_paths[0], force="mesh")
        assert final_mesh.volume < scaled_mesh.volume

    def test_original_input_file_is_untouched(
        self, box_with_known_dims: Path, tmp_path: Path
    ):
        # Read original file content before operations
        original_mesh = trimesh.load(str(box_with_known_dims), force="mesh")
        original_volume = original_mesh.volume
        original_vertex_count = len(original_mesh.vertices)
        original_face_count = len(original_mesh.faces)

        # Step 1: Scale
        scaled_output = str(tmp_path / "chain_orig_scaled.stl")
        scale_result = modify_mesh(
            mesh_path=str(box_with_known_dims),
            operation="scale",
            output_path=scaled_output,
            scale_mode="uniform",
            factor=1.2,
        )

        # Step 2: Boolean
        bool_output = str(tmp_path / "chain_orig_bool.stl")
        modify_mesh(
            mesh_path=scale_result.output_mesh_paths[0],
            operation="boolean",
            output_path=bool_output,
            boolean_type="difference",
            primitive_type="cylinder",
            primitive_dimensions={"diameter": 6.0, "height": 30.0},
            primitive_position=(0.0, 0.0, 0.0),
        )

        # Re-read original file and compare
        after_mesh = trimesh.load(str(box_with_known_dims), force="mesh")
        assert len(after_mesh.vertices) == original_vertex_count
        assert len(after_mesh.faces) == original_face_count
        assert abs(after_mesh.volume - original_volume) < 1e-6

    def test_output_paths_chain_correctly(
        self, box_with_known_dims: Path, tmp_path: Path
    ):
        # Step 1: Scale
        scaled_output = str(tmp_path / "chain_path_scaled.stl")
        scale_result = modify_mesh(
            mesh_path=str(box_with_known_dims),
            operation="scale",
            output_path=scaled_output,
            scale_mode="uniform",
            factor=1.2,
        )

        # Step 2: Boolean using Step 1's output as input
        bool_output = str(tmp_path / "chain_path_bool.stl")
        bool_result = modify_mesh(
            mesh_path=scale_result.output_mesh_paths[0],
            operation="boolean",
            output_path=bool_output,
            boolean_type="difference",
            primitive_type="cylinder",
            primitive_dimensions={"diameter": 6.0, "height": 30.0},
            primitive_position=(0.0, 0.0, 0.0),
        )

        # The boolean input should be the scale output
        assert bool_result.input_mesh_path == str(
            Path(scale_result.output_mesh_paths[0]).resolve()
        )
        # The final output path should differ from both input and intermediate
        assert bool_result.output_mesh_paths[0] != scale_result.output_mesh_paths[0]
        assert bool_result.output_mesh_paths[0] != str(box_with_known_dims)
        assert os.path.exists(bool_result.output_mesh_paths[0])
