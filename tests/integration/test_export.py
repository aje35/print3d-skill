"""Integration tests for the export_mesh() public API.

End-to-end tests that exercise the full export pipeline including mesh loading,
format selection, output directory creation, and result structure validation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from print3d_skill.exceptions import UnsupportedFormatError
from print3d_skill.export import export_mesh
from print3d_skill.models.analysis import MeshAnalysisReport
from print3d_skill.models.export import ExportResult


# ---------------------------------------------------------------------------
# STL export
# ---------------------------------------------------------------------------

class TestStlExport:
    def test_stl_key_present_in_result_paths(self, clean_mesh: Path, tmp_path: Path):
        result = export_mesh(str(clean_mesh), output_dir=str(tmp_path), formats=["stl"])

        assert "stl" in result.paths

    def test_stl_output_file_exists_on_disk(self, clean_mesh: Path, tmp_path: Path):
        result = export_mesh(str(clean_mesh), output_dir=str(tmp_path), formats=["stl"])

        assert Path(result.paths["stl"]).exists()

    def test_stl_output_file_is_non_empty(self, clean_mesh: Path, tmp_path: Path):
        result = export_mesh(str(clean_mesh), output_dir=str(tmp_path), formats=["stl"])

        assert Path(result.paths["stl"]).stat().st_size > 0


# ---------------------------------------------------------------------------
# 3MF export
# ---------------------------------------------------------------------------

class TestThreeMfExport:
    def test_3mf_key_present_in_result_paths(self, clean_mesh: Path, tmp_path: Path):
        result = export_mesh(str(clean_mesh), output_dir=str(tmp_path), formats=["3mf"])

        assert "3mf" in result.paths

    def test_3mf_output_file_exists_on_disk(self, clean_mesh: Path, tmp_path: Path):
        result = export_mesh(str(clean_mesh), output_dir=str(tmp_path), formats=["3mf"])

        assert Path(result.paths["3mf"]).exists()

    def test_3mf_output_file_is_non_empty(self, clean_mesh: Path, tmp_path: Path):
        result = export_mesh(str(clean_mesh), output_dir=str(tmp_path), formats=["3mf"])

        assert Path(result.paths["3mf"]).stat().st_size > 0


# ---------------------------------------------------------------------------
# Multi-format export (default formats)
# ---------------------------------------------------------------------------

class TestMultiFormatExport:
    def test_default_formats_produce_both_stl_and_3mf_keys(
        self, clean_mesh: Path, tmp_path: Path
    ):
        # export_mesh defaults to ["stl", "3mf"] when formats is None
        result = export_mesh(str(clean_mesh), output_dir=str(tmp_path))

        assert "stl" in result.paths
        assert "3mf" in result.paths

    def test_default_formats_both_output_files_exist(
        self, clean_mesh: Path, tmp_path: Path
    ):
        result = export_mesh(str(clean_mesh), output_dir=str(tmp_path))

        assert Path(result.paths["stl"]).exists()
        assert Path(result.paths["3mf"]).exists()

    def test_explicit_multi_format_list_produces_all_requested_keys(
        self, clean_mesh: Path, tmp_path: Path
    ):
        result = export_mesh(
            str(clean_mesh), output_dir=str(tmp_path), formats=["stl", "3mf"]
        )

        assert set(result.paths.keys()) == {"stl", "3mf"}

    def test_paths_dict_length_matches_number_of_requested_formats(
        self, clean_mesh: Path, tmp_path: Path
    ):
        result = export_mesh(
            str(clean_mesh), output_dir=str(tmp_path), formats=["stl", "3mf"]
        )

        assert len(result.paths) == 2


# ---------------------------------------------------------------------------
# Output directory creation
# ---------------------------------------------------------------------------

class TestOutputDirectoryCreation:
    def test_nonexistent_subdirectory_is_created_automatically(
        self, clean_mesh: Path, tmp_path: Path
    ):
        # The sub-directory does not exist before the call
        new_subdir = tmp_path / "nested" / "output"
        assert not new_subdir.exists()

        export_mesh(str(clean_mesh), output_dir=str(new_subdir), formats=["stl"])

        assert new_subdir.is_dir()

    def test_exported_file_lands_inside_the_created_directory(
        self, clean_mesh: Path, tmp_path: Path
    ):
        new_subdir = tmp_path / "created_on_demand"

        result = export_mesh(
            str(clean_mesh), output_dir=str(new_subdir), formats=["stl"]
        )

        exported_path = Path(result.paths["stl"])
        assert exported_path.parent.resolve() == new_subdir.resolve()


# ---------------------------------------------------------------------------
# ExportResult structure
# ---------------------------------------------------------------------------

class TestExportResultStructure:
    def test_result_is_export_result_instance(self, clean_mesh: Path, tmp_path: Path):
        result = export_mesh(str(clean_mesh), output_dir=str(tmp_path), formats=["stl"])

        assert isinstance(result, ExportResult)

    def test_analysis_report_is_not_none(self, clean_mesh: Path, tmp_path: Path):
        result = export_mesh(str(clean_mesh), output_dir=str(tmp_path), formats=["stl"])

        assert result.analysis_report is not None

    def test_analysis_report_is_mesh_analysis_report_instance(
        self, clean_mesh: Path, tmp_path: Path
    ):
        result = export_mesh(str(clean_mesh), output_dir=str(tmp_path), formats=["stl"])

        assert isinstance(result.analysis_report, MeshAnalysisReport)

    def test_repair_summary_is_none(self, clean_mesh: Path, tmp_path: Path):
        # export_mesh never performs repairs; repair_summary must always be None
        result = export_mesh(str(clean_mesh), output_dir=str(tmp_path), formats=["stl"])

        assert result.repair_summary is None

    def test_paths_values_are_absolute(self, clean_mesh: Path, tmp_path: Path):
        result = export_mesh(
            str(clean_mesh), output_dir=str(tmp_path), formats=["stl", "3mf"]
        )

        for fmt, path_str in result.paths.items():
            assert Path(path_str).is_absolute(), (
                f"Expected absolute path for format '{fmt}', got: {path_str}"
            )

    def test_analysis_report_reflects_input_mesh_format(
        self, clean_mesh: Path, tmp_path: Path
    ):
        # clean_mesh is an STL file; the analysis report should record this
        result = export_mesh(str(clean_mesh), output_dir=str(tmp_path), formats=["stl"])

        assert result.analysis_report.format == "stl"


# ---------------------------------------------------------------------------
# FileNotFoundError
# ---------------------------------------------------------------------------

class TestFileNotFoundError:
    def test_nonexistent_path_raises_file_not_found(self, tmp_path: Path):
        missing = str(tmp_path / "does_not_exist.stl")

        with pytest.raises(FileNotFoundError):
            export_mesh(missing)

    def test_error_message_contains_the_missing_path(self, tmp_path: Path):
        missing = str(tmp_path / "ghost.stl")

        with pytest.raises(FileNotFoundError, match="ghost.stl"):
            export_mesh(missing)


# ---------------------------------------------------------------------------
# UnsupportedFormatError
# ---------------------------------------------------------------------------

class TestUnsupportedFormatError:
    def test_step_file_raises_unsupported_format_error(self, tmp_path: Path):
        # .step is not in the supported set {stl, 3mf, obj, ply}
        step_file = tmp_path / "model.step"
        step_file.write_text("ISO-10303-21; fake STEP content")

        with pytest.raises(UnsupportedFormatError):
            export_mesh(str(step_file))

    def test_unknown_extension_also_raises_unsupported_format_error(
        self, tmp_path: Path
    ):
        unknown_file = tmp_path / "model.xyz"
        unknown_file.write_text("not a mesh")

        with pytest.raises(UnsupportedFormatError):
            export_mesh(str(unknown_file))
