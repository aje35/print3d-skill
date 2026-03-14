"""Integration tests for the slicer CLI pipeline (slice_model public API).

These tests cover four scenarios:

1. Full pipeline (slicer available): slice a real STL model, validate the
   SliceResult structure, and confirm the output G-code file exists on disk.
   Skipped automatically when neither prusa-slicer nor orca-slicer is on PATH.

2. No slicer available: patch both backend detect() methods to return False,
   then assert CapabilityUnavailable is raised by slice_model().

3. Unsupported file format: slice_model() must raise UnsupportedFormatError
   for any extension that is not .stl or .3mf (e.g., .obj, .step, .xyz).

4. Missing model file: slice_model() must raise FileNotFoundError when the
   model path does not point to an existing file.

Design notes
------------
- Scenarios 3 and 4 are validated before any slicer detection occurs (the
  extension and existence checks are the first gates in slice_model()), so
  they run unconditionally without mocking.
- Scenario 2 uses unittest.mock.patch to isolate the detection layer;
  subprocess is never called.
- The full pipeline test (scenario 1) requires a real slicer binary and uses
  a programmatically generated STL cube so there are no binary fixtures
  checked into the repo.  G-code validation confirms the file is non-empty
  and contains at least one movement command (G0 or G1).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
import trimesh

from print3d_skill.exceptions import CapabilityUnavailable, UnsupportedFormatError
from print3d_skill.models.validate import SliceResult, SlicerType
from print3d_skill.slicing import slice_model

# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

_PRUSA_AVAILABLE = (
    shutil.which("prusa-slicer") is not None or shutil.which("PrusaSlicer") is not None
)
_ORCA_AVAILABLE = shutil.which("orca-slicer") is not None or shutil.which("OrcaSlicer") is not None
_ANY_SLICER_AVAILABLE = _PRUSA_AVAILABLE or _ORCA_AVAILABLE

_SKIP_NO_SLICER = pytest.mark.skipif(
    not _ANY_SLICER_AVAILABLE,
    reason="No slicer CLI found (prusa-slicer or orca-slicer not on PATH)",
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def cube_stl_for_slicing(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a minimal 20x20x20 mm STL cube for slicing tests.

    Uses a module-scoped tmp directory so the same file is reused across
    all tests in this module, avoiding redundant I/O.
    """
    mesh = trimesh.creation.box(extents=[20, 20, 20])
    path = tmp_path_factory.mktemp("slicing_meshes") / "cube_for_slicing.stl"
    mesh.export(str(path), file_type="stl")
    return path


# ---------------------------------------------------------------------------
# Scenario 1 — Full pipeline with a real slicer
# ---------------------------------------------------------------------------


@_SKIP_NO_SLICER
class TestFullSlicingPipeline:
    """Slice a real STL model and validate the complete output.

    These tests are skipped automatically when no slicer binary is available.
    When a slicer is present, they exercise the full path from slice_model()
    through subprocess invocation, G-code file creation, and SliceResult
    population.
    """

    def test_returns_slice_result_instance(self, cube_stl_for_slicing: Path, tmp_path: Path):
        # Arrange
        out = tmp_path / "cube_sliced.gcode"

        # Act
        result = slice_model(str(cube_stl_for_slicing), output_path=str(out))

        # Assert
        assert isinstance(result, SliceResult)

    def test_gcode_file_exists_on_disk(self, cube_stl_for_slicing: Path, tmp_path: Path):
        out = tmp_path / "cube_sliced.gcode"

        result = slice_model(str(cube_stl_for_slicing), output_path=str(out))

        assert Path(result.gcode_path).exists(), (
            f"Expected G-code output at {result.gcode_path!r} but file was not created"
        )

    def test_gcode_file_has_non_zero_size(self, cube_stl_for_slicing: Path, tmp_path: Path):
        # A sliced model always produces at least a header and a few move commands.
        out = tmp_path / "cube_sliced.gcode"

        result = slice_model(str(cube_stl_for_slicing), output_path=str(out))

        assert Path(result.gcode_path).stat().st_size > 0

    def test_gcode_file_contains_movement_commands(
        self, cube_stl_for_slicing: Path, tmp_path: Path
    ):
        # Every valid G-code file produced by a slicer must contain at least
        # one G0 (rapid move) or G1 (linear move) command.
        out = tmp_path / "cube_sliced.gcode"

        result = slice_model(str(cube_stl_for_slicing), output_path=str(out))

        gcode_text = Path(result.gcode_path).read_text(errors="replace")
        has_moves = any(
            line.startswith(("G0 ", "G0\t", "G1 ", "G1\t", "G0\n", "G1\n"))
            for line in gcode_text.splitlines()
        )
        assert has_moves, (
            "Sliced G-code does not contain any G0/G1 movement commands. "
            f"File path: {result.gcode_path!r}"
        )

    def test_result_gcode_path_matches_requested_output(
        self, cube_stl_for_slicing: Path, tmp_path: Path
    ):
        out = tmp_path / "cube_sliced.gcode"

        result = slice_model(str(cube_stl_for_slicing), output_path=str(out))

        assert Path(result.gcode_path).resolve() == out.resolve()

    def test_result_model_path_matches_input(self, cube_stl_for_slicing: Path, tmp_path: Path):
        out = tmp_path / "cube_sliced.gcode"

        result = slice_model(str(cube_stl_for_slicing), output_path=str(out))

        assert Path(result.model_path).resolve() == cube_stl_for_slicing.resolve()

    def test_result_slicer_used_is_valid_slicer_type(
        self, cube_stl_for_slicing: Path, tmp_path: Path
    ):
        out = tmp_path / "cube_sliced.gcode"

        result = slice_model(str(cube_stl_for_slicing), output_path=str(out))

        assert isinstance(result.slicer_used, SlicerType)
        assert result.slicer_used in (SlicerType.PRUSASLICER, SlicerType.ORCASLICER)

    def test_result_slicer_version_is_string(self, cube_stl_for_slicing: Path, tmp_path: Path):
        # slicer_version may be an empty string if version detection fails,
        # but it must always be a str, never None.
        out = tmp_path / "cube_sliced.gcode"

        result = slice_model(str(cube_stl_for_slicing), output_path=str(out))

        assert isinstance(result.slicer_version, str)

    def test_result_profiles_used_is_dict(self, cube_stl_for_slicing: Path, tmp_path: Path):
        # Without explicit profiles, profiles_used should be an empty dict.
        out = tmp_path / "cube_sliced.gcode"

        result = slice_model(str(cube_stl_for_slicing), output_path=str(out))

        assert isinstance(result.profiles_used, dict)

    def test_result_overrides_applied_is_dict(self, cube_stl_for_slicing: Path, tmp_path: Path):
        # Without overrides, overrides_applied should be an empty dict.
        out = tmp_path / "cube_sliced.gcode"

        result = slice_model(str(cube_stl_for_slicing), output_path=str(out))

        assert isinstance(result.overrides_applied, dict)

    def test_result_warnings_is_list(self, cube_stl_for_slicing: Path, tmp_path: Path):
        out = tmp_path / "cube_sliced.gcode"

        result = slice_model(str(cube_stl_for_slicing), output_path=str(out))

        assert isinstance(result.warnings, list)

    def test_output_path_defaults_to_sibling_of_model(self, cube_stl_for_slicing: Path):
        # When output_path is None, slice_model generates a path alongside the
        # input file: <model_stem>_sliced.gcode in the same directory.
        expected_default = cube_stl_for_slicing.parent / (
            cube_stl_for_slicing.stem + "_sliced.gcode"
        )

        result = slice_model(str(cube_stl_for_slicing))

        assert Path(result.gcode_path).resolve() == expected_default.resolve()
        # Clean up the auto-generated file after the test
        expected_default.unlink(missing_ok=True)

    def test_accepts_path_object_as_model_path(self, cube_stl_for_slicing: Path, tmp_path: Path):
        # slice_model accepts both str and Path for model_path.
        out = tmp_path / "cube_sliced_path_obj.gcode"

        result = slice_model(cube_stl_for_slicing, output_path=str(out))

        assert isinstance(result, SliceResult)
        assert Path(result.gcode_path).exists()

    def test_accepts_path_object_as_output_path(self, cube_stl_for_slicing: Path, tmp_path: Path):
        # output_path also accepts a Path object.
        out = tmp_path / "cube_sliced_out_path_obj.gcode"

        result = slice_model(str(cube_stl_for_slicing), output_path=out)

        assert isinstance(result, SliceResult)
        assert Path(result.gcode_path).exists()


# ---------------------------------------------------------------------------
# Scenario 2 — No slicer available: CapabilityUnavailable raised
# ---------------------------------------------------------------------------


class TestNoSlicerAvailable:
    """When all slicer backends report unavailability, slice_model() must
    raise CapabilityUnavailable.  Both backend detect() methods are patched
    to return False so the test runs regardless of the host environment.
    """

    def test_raises_capability_unavailable_when_no_slicer_detected(
        self, cube_stl_for_slicing: Path, tmp_path: Path
    ):
        # Arrange: patch both backend detect() calls to simulate a system
        # where neither PrusaSlicer nor OrcaSlicer is installed.
        with (
            patch(
                "print3d_skill.slicing.prusaslicer.PrusaSlicerBackend.detect",
                return_value=False,
            ),
            patch(
                "print3d_skill.slicing.orcaslicer.OrcaSlicerBackend.detect",
                return_value=False,
            ),
        ):
            # Act / Assert
            with pytest.raises(CapabilityUnavailable):
                slice_model(
                    str(cube_stl_for_slicing),
                    output_path=str(tmp_path / "out.gcode"),
                )

    def test_capability_unavailable_has_gcode_slicing_capability(
        self, cube_stl_for_slicing: Path, tmp_path: Path
    ):
        # The exception's .capability attribute must identify what is missing.
        with (
            patch(
                "print3d_skill.slicing.prusaslicer.PrusaSlicerBackend.detect",
                return_value=False,
            ),
            patch(
                "print3d_skill.slicing.orcaslicer.OrcaSlicerBackend.detect",
                return_value=False,
            ),
        ):
            with pytest.raises(CapabilityUnavailable) as exc_info:
                slice_model(
                    str(cube_stl_for_slicing),
                    output_path=str(tmp_path / "out.gcode"),
                )

        assert exc_info.value.capability == "gcode_slicing"

    def test_capability_unavailable_message_mentions_slicer(
        self, cube_stl_for_slicing: Path, tmp_path: Path
    ):
        # The human-readable exception message must include the word "slicer"
        # so that callers can surface a meaningful error to users.
        with (
            patch(
                "print3d_skill.slicing.prusaslicer.PrusaSlicerBackend.detect",
                return_value=False,
            ),
            patch(
                "print3d_skill.slicing.orcaslicer.OrcaSlicerBackend.detect",
                return_value=False,
            ),
        ):
            with pytest.raises(CapabilityUnavailable) as exc_info:
                slice_model(
                    str(cube_stl_for_slicing),
                    output_path=str(tmp_path / "out.gcode"),
                )

        assert "slicer" in str(exc_info.value).lower()

    def test_capability_unavailable_raised_for_explicit_prusaslicer_when_absent(
        self, cube_stl_for_slicing: Path, tmp_path: Path
    ):
        # When forcing SlicerType.PRUSASLICER but it is not available,
        # CapabilityUnavailable must still be raised.
        with patch(
            "print3d_skill.slicing.prusaslicer.PrusaSlicerBackend.detect",
            return_value=False,
        ):
            with pytest.raises(CapabilityUnavailable) as exc_info:
                slice_model(
                    str(cube_stl_for_slicing),
                    output_path=str(tmp_path / "out.gcode"),
                    slicer=SlicerType.PRUSASLICER,
                )

        assert exc_info.value.capability == "gcode_slicing"

    def test_capability_unavailable_raised_for_explicit_orcaslicer_when_absent(
        self, cube_stl_for_slicing: Path, tmp_path: Path
    ):
        # When forcing SlicerType.ORCASLICER but it is not available,
        # CapabilityUnavailable must still be raised.
        with patch(
            "print3d_skill.slicing.orcaslicer.OrcaSlicerBackend.detect",
            return_value=False,
        ):
            with pytest.raises(CapabilityUnavailable) as exc_info:
                slice_model(
                    str(cube_stl_for_slicing),
                    output_path=str(tmp_path / "out.gcode"),
                    slicer=SlicerType.ORCASLICER,
                )

        assert exc_info.value.capability == "gcode_slicing"

    def test_capability_unavailable_is_print3d_skill_error(
        self, cube_stl_for_slicing: Path, tmp_path: Path
    ):
        # CapabilityUnavailable must inherit from Print3DSkillError so callers
        # can use a single broad except clause.
        from print3d_skill.exceptions import Print3DSkillError

        with (
            patch(
                "print3d_skill.slicing.prusaslicer.PrusaSlicerBackend.detect",
                return_value=False,
            ),
            patch(
                "print3d_skill.slicing.orcaslicer.OrcaSlicerBackend.detect",
                return_value=False,
            ),
        ):
            with pytest.raises(Print3DSkillError):
                slice_model(
                    str(cube_stl_for_slicing),
                    output_path=str(tmp_path / "out.gcode"),
                )


# ---------------------------------------------------------------------------
# Scenario 3 — Unsupported file format: UnsupportedFormatError raised
# ---------------------------------------------------------------------------


class TestUnsupportedFormatError:
    """slice_model() must reject files with extensions other than .stl/.3mf
    before attempting any slicer detection.  These tests run unconditionally
    because the format check happens before the capability check.
    """

    @pytest.mark.parametrize("extension", [".obj", ".step", ".ply", ".xyz", ".step", ".amf"])
    def test_raises_for_unsupported_extension(self, extension: str, tmp_path: Path):
        # Arrange: create a file with the offending extension so the
        # existence check passes; only the format gate should fire.
        model_file = tmp_path / f"model{extension}"
        model_file.write_text("not a real mesh")

        # Act / Assert
        with pytest.raises(UnsupportedFormatError):
            slice_model(str(model_file))

    def test_unsupported_format_error_message_contains_extension(self, tmp_path: Path):
        # The exception message should name the rejected extension so the
        # caller can construct a useful error report.
        model_file = tmp_path / "model.obj"
        model_file.write_text("not a real mesh")

        with pytest.raises(UnsupportedFormatError) as exc_info:
            slice_model(str(model_file))

        assert ".obj" in str(exc_info.value)

    def test_unsupported_format_error_message_lists_supported_formats(self, tmp_path: Path):
        # The exception message should name the supported formats (.stl, .3mf)
        # to guide the user toward a valid input.
        model_file = tmp_path / "model.step"
        model_file.write_text("ISO-10303-21;")

        with pytest.raises(UnsupportedFormatError) as exc_info:
            slice_model(str(model_file))

        error_text = str(exc_info.value).lower()
        assert "stl" in error_text or "3mf" in error_text

    def test_unsupported_format_error_is_print3d_skill_error(self, tmp_path: Path):
        from print3d_skill.exceptions import Print3DSkillError

        model_file = tmp_path / "model.xyz"
        model_file.write_text("garbage")

        with pytest.raises(Print3DSkillError):
            slice_model(str(model_file))

    def test_no_subprocess_called_for_unsupported_format(self, tmp_path: Path):
        # Verify the check is a pure guard: subprocess must never be invoked
        # for an unsupported extension, even if a slicer is installed.
        model_file = tmp_path / "model.ply"
        model_file.write_text("ply format")

        with patch("subprocess.run") as mock_run:
            with pytest.raises(UnsupportedFormatError):
                slice_model(str(model_file))

        mock_run.assert_not_called()

    def test_stl_extension_is_accepted(self, tmp_path: Path):
        # .stl is a supported format; slice_model should proceed past the
        # format guard.  We mock backend detection so the test stays
        # unconditional and doesn't need a real slicer.
        model_file = tmp_path / "model.stl"
        model_file.write_text("solid fake\nendsolid fake\n")

        with (
            patch(
                "print3d_skill.slicing.prusaslicer.PrusaSlicerBackend.detect",
                return_value=False,
            ),
            patch(
                "print3d_skill.slicing.orcaslicer.OrcaSlicerBackend.detect",
                return_value=False,
            ),
        ):
            # The format gate passes; CapabilityUnavailable is expected next.
            with pytest.raises(CapabilityUnavailable):
                slice_model(str(model_file))

    def test_3mf_extension_is_accepted(self, tmp_path: Path):
        # .3mf is a supported format; slice_model should proceed past the
        # format guard.  We patch backend detection to avoid needing a slicer.
        model_file = tmp_path / "model.3mf"
        model_file.write_bytes(b"PK\x03\x04fake 3mf zip content")

        with (
            patch(
                "print3d_skill.slicing.prusaslicer.PrusaSlicerBackend.detect",
                return_value=False,
            ),
            patch(
                "print3d_skill.slicing.orcaslicer.OrcaSlicerBackend.detect",
                return_value=False,
            ),
        ):
            with pytest.raises(CapabilityUnavailable):
                slice_model(str(model_file))

    def test_extension_check_is_case_insensitive(self, tmp_path: Path):
        # Uppercase .STL should be treated as .stl (supported), not rejected.
        model_file = tmp_path / "model.STL"
        model_file.write_text("solid fake\nendsolid fake\n")

        with (
            patch(
                "print3d_skill.slicing.prusaslicer.PrusaSlicerBackend.detect",
                return_value=False,
            ),
            patch(
                "print3d_skill.slicing.orcaslicer.OrcaSlicerBackend.detect",
                return_value=False,
            ),
        ):
            # CapabilityUnavailable means the format gate passed correctly.
            with pytest.raises(CapabilityUnavailable):
                slice_model(str(model_file))


# ---------------------------------------------------------------------------
# Scenario 4 — Missing model file: FileNotFoundError raised
# ---------------------------------------------------------------------------


class TestMissingModelFile:
    """slice_model() must raise FileNotFoundError when the model path does
    not point to an existing file.  The existence check fires before both the
    format check and slicer detection, so these tests run unconditionally.
    """

    def test_raises_file_not_found_for_nonexistent_path(self, tmp_path: Path):
        missing = tmp_path / "does_not_exist.stl"

        with pytest.raises(FileNotFoundError):
            slice_model(str(missing))

    def test_raises_file_not_found_for_completely_fictional_path(self):
        with pytest.raises(FileNotFoundError):
            slice_model("/nonexistent/path/to/model.stl")

    def test_raises_file_not_found_for_directory_path(self, tmp_path: Path):
        # tmp_path is a directory, not a file; is_file() returns False.
        with pytest.raises(FileNotFoundError):
            slice_model(str(tmp_path))

    def test_file_not_found_error_message_contains_path(self, tmp_path: Path):
        missing = tmp_path / "missing_model.stl"

        with pytest.raises(FileNotFoundError) as exc_info:
            slice_model(str(missing))

        assert "missing_model.stl" in str(exc_info.value)

    def test_no_subprocess_called_for_missing_file(self, tmp_path: Path):
        # Confirm that subprocess is never invoked when the file doesn't exist.
        missing = tmp_path / "does_not_exist.stl"

        with patch("subprocess.run") as mock_run:
            with pytest.raises(FileNotFoundError):
                slice_model(str(missing))

        mock_run.assert_not_called()

    def test_raises_file_not_found_before_format_check(self, tmp_path: Path):
        # A missing file with an unsupported extension should raise
        # FileNotFoundError (existence check) rather than UnsupportedFormatError
        # (format check), confirming the ordering of guards.
        missing = tmp_path / "missing_model.xyz"

        with pytest.raises(FileNotFoundError):
            slice_model(str(missing))

    def test_existing_file_passes_existence_check(self, tmp_path: Path):
        # An existing file with an unsupported format should raise
        # UnsupportedFormatError rather than FileNotFoundError, confirming
        # the existence guard only fires for missing files.
        existing = tmp_path / "present_model.obj"
        existing.write_text("v 0 0 0\n")

        with pytest.raises(UnsupportedFormatError):
            slice_model(str(existing))

    @pytest.mark.parametrize(
        "path_arg",
        [
            "/tmp/absolutely/nonexistent/path/model.stl",
            "/var/run/print3d_nonexistent_model.stl",
        ],
    )
    def test_raises_file_not_found_for_various_missing_paths(self, path_arg: str):
        with pytest.raises(FileNotFoundError):
            slice_model(path_arg)
