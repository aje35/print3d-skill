"""Integration tests for the rendering pipeline (US1).

Tests STL → PNG end-to-end rendering, format handling,
error cases, and unit detection warnings.
"""

from __future__ import annotations

import os
import shutil

import pytest
from PIL import Image

from print3d_skill import render_preview
from print3d_skill.exceptions import (
    CapabilityUnavailable,
    MeshLoadError,
    UnsupportedFormatError,
)


class TestSTLRendering:
    def test_cube_stl_produces_valid_png(self, cube_stl, tmp_output_dir):
        out = tmp_output_dir / "cube_preview.png"
        result = render_preview(str(cube_stl), str(out))

        assert os.path.exists(result.image_path)
        img = Image.open(result.image_path)
        assert img.size == (1600, 1200)

    def test_result_metadata(self, cube_stl, tmp_output_dir):
        out = tmp_output_dir / "cube_meta.png"
        result = render_preview(str(cube_stl), str(out))

        assert result.resolution == (1600, 1200)
        assert result.file_size_bytes > 0
        assert result.file_size_bytes < 1_000_000
        assert len(result.views) == 4
        assert result.render_time_seconds > 0
        assert result.timed_out is False

    def test_four_view_names(self, cube_stl, tmp_output_dir):
        out = tmp_output_dir / "cube_views.png"
        result = render_preview(str(cube_stl), str(out))
        names = {v.name for v in result.views}
        assert names == {"front", "side", "top", "isometric"}

    def test_mesh_summary(self, cube_stl, tmp_output_dir):
        out = tmp_output_dir / "cube_summary.png"
        result = render_preview(str(cube_stl), str(out))
        assert result.mesh_summary.face_count == 12
        assert result.mesh_summary.vertex_count == 8


class TestOBJRendering:
    def test_obj_renders_successfully(self, simple_obj, tmp_output_dir):
        out = tmp_output_dir / "obj_preview.png"
        result = render_preview(str(simple_obj), str(out))

        assert os.path.exists(result.image_path)
        assert result.mesh_summary.face_count > 0


class Test3MFRendering:
    def test_3mf_renders_successfully(self, colored_3mf, tmp_output_dir):
        out = tmp_output_dir / "3mf_preview.png"
        result = render_preview(str(colored_3mf), str(out))

        assert os.path.exists(result.image_path)
        assert result.mesh_summary.face_count > 0


class TestErrorHandling:
    def test_missing_file_raises_file_not_found(self, tmp_output_dir):
        with pytest.raises(FileNotFoundError):
            render_preview("/nonexistent/model.stl", str(tmp_output_dir / "out.png"))

    def test_corrupt_stl_raises_mesh_load_error(self, corrupt_stl, tmp_output_dir):
        with pytest.raises(MeshLoadError):
            render_preview(str(corrupt_stl), str(tmp_output_dir / "corrupt.png"))

    def test_unsupported_format_raises_error(self, tmp_path):
        bad_file = tmp_path / "model.xyz"
        bad_file.write_text("not a mesh")
        with pytest.raises(UnsupportedFormatError):
            render_preview(str(bad_file), str(tmp_path / "out.png"))


class TestUnitDetection:
    def test_tiny_mesh_warns_about_meters(self, tiny_mesh, tmp_output_dir):
        out = tmp_output_dir / "tiny_preview.png"
        result = render_preview(str(tiny_mesh), str(out))

        assert len(result.warnings) > 0
        assert any("meters" in w.lower() or "small" in w.lower() for w in result.warnings)


class TestScadRendering:
    @pytest.mark.skipif(
        not shutil.which("openscad"),
        reason="OpenSCAD not installed",
    )
    def test_scad_renders_if_openscad_available(self, sample_scad, tmp_output_dir):
        out = tmp_output_dir / "scad_preview.png"
        result = render_preview(str(sample_scad), str(out))
        assert os.path.exists(result.image_path)

    @pytest.mark.skipif(
        shutil.which("openscad") is not None,
        reason="OpenSCAD is installed (cannot test missing case)",
    )
    def test_scad_without_openscad_raises_capability_unavailable(
        self, sample_scad, tmp_output_dir
    ):
        with pytest.raises(CapabilityUnavailable):
            render_preview(str(sample_scad), str(tmp_output_dir / "scad.png"))


class TestCustomResolution:
    def test_custom_resolution(self, cube_stl, tmp_output_dir):
        out = tmp_output_dir / "custom_res.png"
        result = render_preview(str(cube_stl), str(out), resolution=(800, 600))

        assert result.resolution == (800, 600)
        img = Image.open(result.image_path)
        assert img.size == (800, 600)
