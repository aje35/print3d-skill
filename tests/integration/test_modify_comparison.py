"""Integration tests for Modify mode visual comparison output (T039, T040).

Validates that before/after preview rendering produces structurally
correct PNG images with matching dimensions across boolean and split operations.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from print3d_skill import modify_mesh


class TestComparisonOutputStructure:
    """T039: Boolean operation produces valid before/after comparison previews."""

    def test_boolean_subtract_comparison_previews(self, cube_stl: Path, tmp_path: Path):
        result = modify_mesh(
            mesh_path=str(cube_stl),
            operation="boolean",
            output_path=str(tmp_path / "cube_subtracted.stl"),
            boolean_type="difference",
            primitive_type="cylinder",
            primitive_dimensions={"diameter": 10.0, "height": 30.0},
        )

        # before_preview_path exists and is a non-zero PNG
        before = Path(result.before_preview_path)
        assert before.exists(), "before_preview_path does not exist"
        assert before.stat().st_size > 0, "before preview PNG is empty"
        assert before.suffix.lower() == ".png"

        # after_preview_paths has at least 1 entry, each a non-zero PNG
        assert len(result.after_preview_paths) >= 1
        for after_path in result.after_preview_paths:
            p = Path(after_path)
            assert p.exists(), f"after preview does not exist: {after_path}"
            assert p.stat().st_size > 0, f"after preview PNG is empty: {after_path}"
            assert p.suffix.lower() == ".png"

        # Before and after images have matching dimensions
        before_img = Image.open(result.before_preview_path)
        for after_path in result.after_preview_paths:
            after_img = Image.open(after_path)
            assert before_img.size == after_img.size, (
                f"Dimension mismatch: before={before_img.size}, after={after_img.size}"
            )


class TestSplitComparisonValidation:
    """T040: Split operation produces per-part comparison previews."""

    def test_split_produces_per_part_previews(self, tall_box_stl: Path, tmp_path: Path):
        result = modify_mesh(
            mesh_path=str(tall_box_stl),
            operation="split",
            split_axis="z",
            split_offset_mm=50.0,
        )

        # Per-part previews rendered (at least 2 for a split)
        assert len(result.after_preview_paths) >= 2, (
            f"Expected at least 2 after previews, got {len(result.after_preview_paths)}"
        )

        # All preview PNGs are non-zero size
        for after_path in result.after_preview_paths:
            p = Path(after_path)
            assert p.exists(), f"Part preview does not exist: {after_path}"
            assert p.stat().st_size > 0, f"Part preview PNG is empty: {after_path}"

        # after_preview_paths has entries for each output part
        assert len(result.after_preview_paths) == len(result.output_mesh_paths), (
            f"Preview count ({len(result.after_preview_paths)}) does not match "
            f"part count ({len(result.output_mesh_paths)})"
        )
