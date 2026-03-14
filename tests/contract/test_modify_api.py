"""T041 – Contract tests for the modify_mesh() public API.

Verifies the function signature, return type fields, and error
contracts (FileNotFoundError, ValueError, UnsupportedFormatError,
CapabilityUnavailable).
"""

from __future__ import annotations

import shutil

import pytest

from print3d_skill import modify_mesh
from print3d_skill.exceptions import CapabilityUnavailable, UnsupportedFormatError
from print3d_skill.models.modify import ModifyOperation, ModifyResult


class TestModifyMeshSignature:
    """modify_mesh with a no-op scale returns ModifyResult with all documented fields."""

    def test_returns_modify_result_with_all_fields(self, cube_stl, tmp_path):
        result = modify_mesh(
            mesh_path=str(cube_stl),
            operation="scale",
            scale_mode="uniform",
            factor=1.0,
            output_dir=str(tmp_path),
        )

        assert isinstance(result, ModifyResult)

        # operation
        assert isinstance(result.operation, ModifyOperation)

        # input_mesh_path
        assert isinstance(result.input_mesh_path, str)

        # output_mesh_paths
        assert isinstance(result.output_mesh_paths, list)
        assert len(result.output_mesh_paths) > 0
        assert all(isinstance(p, str) for p in result.output_mesh_paths)

        # before_preview_path
        assert isinstance(result.before_preview_path, str)

        # after_preview_paths
        assert isinstance(result.after_preview_paths, list)
        assert all(isinstance(p, str) for p in result.after_preview_paths)

        # analysis_report
        from print3d_skill.models.analysis import MeshAnalysisReport

        assert isinstance(result.analysis_report, MeshAnalysisReport)

        # warnings & feature_warnings
        assert isinstance(result.warnings, list)
        assert isinstance(result.feature_warnings, list)

        # bounding boxes
        from print3d_skill.models.mesh import BoundingBox

        assert isinstance(result.bbox_before, BoundingBox)
        assert isinstance(result.bbox_after, BoundingBox)

        # vertex counts
        assert isinstance(result.vertex_count_before, int)
        assert isinstance(result.vertex_count_after, int)

        # face counts
        assert isinstance(result.face_count_before, int)
        assert isinstance(result.face_count_after, int)

        # alignment_features
        assert isinstance(result.alignment_features, list)

        # repair_performed
        assert isinstance(result.repair_performed, bool)


class TestModifyMeshErrorContracts:
    """Error contracts for modify_mesh()."""

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            modify_mesh(
                mesh_path=str(tmp_path / "nonexistent.stl"),
                operation="scale",
                scale_mode="uniform",
                factor=1.0,
                output_dir=str(tmp_path),
            )

    def test_unknown_operation_raises_value_error(self, cube_stl, tmp_path):
        with pytest.raises(ValueError):
            modify_mesh(
                mesh_path=str(cube_stl),
                operation="invalid",
                output_dir=str(tmp_path),
            )

    def test_unsupported_format_raises_error(self, tmp_path):
        txt_file = tmp_path / "model.txt"
        txt_file.write_text("not a mesh")

        with pytest.raises(UnsupportedFormatError):
            modify_mesh(
                mesh_path=str(txt_file),
                operation="scale",
                scale_mode="uniform",
                factor=1.0,
                output_dir=str(tmp_path),
            )


class TestModifyMeshCapabilityUnavailable:
    """CapabilityUnavailable when OpenSCAD is required but not installed."""

    @pytest.mark.skipif(
        shutil.which("openscad") is not None,
        reason="OpenSCAD is installed; cannot test CapabilityUnavailable",
    )
    def test_engrave_without_openscad_raises_capability_unavailable(
        self, cube_stl, tmp_path
    ):
        with pytest.raises(CapabilityUnavailable):
            modify_mesh(
                mesh_path=str(cube_stl),
                operation="engrave",
                text="test",
                output_dir=str(tmp_path),
            )


class TestModifyMeshImportable:
    """modify_mesh is importable from the top-level package."""

    def test_top_level_import(self):
        from print3d_skill import modify_mesh as fn

        assert callable(fn)
