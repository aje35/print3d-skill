"""Unit tests for slicer CLI integration (T024).

Tests cover:
- PrusaSlicer backend: command construction and subprocess invocation
- OrcaSlicer backend: command construction and subprocess invocation
- CapabilityUnavailable when no slicer is found on PATH
- SlicerError on non-zero exit codes and on timeout
- slice_model() auto-detection order (PrusaSlicer before OrcaSlicer)
- FileNotFoundError for missing model files
- UnsupportedFormatError for unsupported file extensions

All subprocess and shutil.which calls are mocked — no real slicer is required.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from print3d_skill.exceptions import (
    CapabilityUnavailable,
    SlicerError,
    UnsupportedFormatError,
)
from print3d_skill.models.validate import SlicerType
from print3d_skill.slicing import slice_model
from print3d_skill.slicing.orcaslicer import OrcaSlicerBackend
from print3d_skill.slicing.prusaslicer import PrusaSlicerBackend

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_completed_process(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    """Build a mock CompletedProcess object for subprocess.run."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


def _make_stl(tmp_path: Path, name: str = "model.stl") -> Path:
    """Create a minimal STL file so is_file() returns True."""
    p = tmp_path / name
    p.write_text("solid test\nendsolid test\n")
    return p


def _make_3mf(tmp_path: Path, name: str = "model.3mf") -> Path:
    """Create a minimal 3MF file so is_file() returns True."""
    p = tmp_path / name
    p.write_bytes(b"PK\x03\x04")  # ZIP magic bytes (3MF is a ZIP)
    return p


# ===========================================================================
# PrusaSlicerBackend
# ===========================================================================


class TestPrusaSlicerDetect:
    """Tests for PrusaSlicerBackend.detect() and _find_executable()."""

    def test_detect_returns_true_when_prusa_slicer_on_path(self):
        with patch(
            "shutil.which",
            side_effect=lambda name: "/usr/bin/prusa-slicer" if name == "prusa-slicer" else None,
        ):
            backend = PrusaSlicerBackend()
            assert backend.detect() is True

    def test_detect_returns_true_when_PrusaSlicer_on_path(self):
        """Handles the capitalised 'PrusaSlicer' executable name."""
        with patch(
            "shutil.which",
            side_effect=lambda name: "/usr/local/bin/PrusaSlicer"
            if name == "PrusaSlicer"
            else None,
        ):
            backend = PrusaSlicerBackend()
            assert backend.detect() is True

    def test_detect_returns_false_when_not_on_path(self):
        with patch("shutil.which", return_value=None):
            backend = PrusaSlicerBackend()
            assert backend.detect() is False

    def test_find_executable_prefers_prusa_slicer_over_PrusaSlicer(self):
        """prusa-slicer (lowercase) is tried before PrusaSlicer."""
        call_log: list[str] = []

        def which_side_effect(name: str) -> str | None:
            call_log.append(name)
            return f"/bin/{name}"  # both found

        with patch("shutil.which", side_effect=which_side_effect):
            backend = PrusaSlicerBackend()
            exe = backend._find_executable()

        assert exe == "prusa-slicer"
        assert call_log[0] == "prusa-slicer"  # checked first


class TestPrusaSlicerGetVersion:
    """Tests for PrusaSlicerBackend.get_version()."""

    def test_returns_version_string_from_stdout(self):
        proc = _make_completed_process(stdout="PrusaSlicer-2.7.1+linux-x64 compiled 2024")
        with (
            patch("shutil.which", return_value="/usr/bin/prusa-slicer"),
            patch("subprocess.run", return_value=proc),
        ):
            backend = PrusaSlicerBackend()
            version = backend.get_version()

        assert version == "PrusaSlicer-2.7.1+linux-x64"

    def test_returns_version_string_from_stderr_when_stdout_empty(self):
        proc = _make_completed_process(stdout="", stderr="2.7.1")
        with (
            patch("shutil.which", return_value="/usr/bin/prusa-slicer"),
            patch("subprocess.run", return_value=proc),
        ):
            version = PrusaSlicerBackend().get_version()

        assert version == "2.7.1"

    def test_returns_none_when_not_found(self):
        with patch("shutil.which", return_value=None):
            assert PrusaSlicerBackend().get_version() is None

    def test_returns_none_on_timeout(self):
        with (
            patch("shutil.which", return_value="/usr/bin/prusa-slicer"),
            patch(
                "subprocess.run",
                side_effect=subprocess.TimeoutExpired(
                    cmd=["prusa-slicer", "--version"], timeout=10
                ),
            ),
        ):
            assert PrusaSlicerBackend().get_version() is None


class TestPrusaSlicerSlice:
    """Tests for PrusaSlicerBackend.slice() command construction."""

    def test_basic_command_includes_export_gcode_and_output(self, tmp_path: Path):
        """Minimal invocation: just model -> output.

        slice() calls subprocess.run twice: once for the actual slice command,
        then once more inside get_version() to retrieve the slicer version.
        call_args_list[0] is always the slice invocation.
        """
        model = _make_stl(tmp_path)
        out = tmp_path / "model_sliced.gcode"
        proc = _make_completed_process()

        with (
            patch("shutil.which", return_value="/usr/bin/prusa-slicer"),
            patch("subprocess.run", return_value=proc) as mock_run,
        ):
            backend = PrusaSlicerBackend()
            backend.slice(model_path=model, output_path=out)

        # First call is the slice command; second call is `--version` inside get_version()
        cmd = mock_run.call_args_list[0][0][0]
        assert cmd[0] == "prusa-slicer"
        assert "--export-gcode" in cmd
        assert "-o" in cmd
        assert str(out) in cmd
        assert str(model) in cmd

    def test_printer_profile_appended_with_load(self, tmp_path: Path):
        model = _make_stl(tmp_path)
        out = tmp_path / "out.gcode"
        proc = _make_completed_process()

        with (
            patch("shutil.which", return_value="/usr/bin/prusa-slicer"),
            patch("subprocess.run", return_value=proc) as mock_run,
        ):
            backend = PrusaSlicerBackend()
            backend.slice(model_path=model, output_path=out, printer_profile="/cfg/printer.ini")

        # Index 0 = slice invocation; index 1 = get_version() --version call
        cmd = mock_run.call_args_list[0][0][0]
        load_idx = cmd.index("--load")
        assert cmd[load_idx + 1] == "/cfg/printer.ini"

    def test_material_and_quality_profiles_appended(self, tmp_path: Path):
        model = _make_stl(tmp_path)
        out = tmp_path / "out.gcode"
        proc = _make_completed_process()

        with (
            patch("shutil.which", return_value="/usr/bin/prusa-slicer"),
            patch("subprocess.run", return_value=proc) as mock_run,
        ):
            backend = PrusaSlicerBackend()
            backend.slice(
                model_path=model,
                output_path=out,
                material_profile="/cfg/pla.ini",
                quality_preset="/cfg/0.2mm.ini",
            )

        # Index 0 = slice invocation; index 1 = get_version() --version call
        cmd = mock_run.call_args_list[0][0][0]
        # Both profiles should appear after --load flags
        load_indices = [i for i, v in enumerate(cmd) if v == "--load"]
        profile_args = [cmd[i + 1] for i in load_indices]
        assert "/cfg/pla.ini" in profile_args
        assert "/cfg/0.2mm.ini" in profile_args

    def test_overrides_written_to_temp_ini_and_loaded(self, tmp_path: Path):
        """Overrides are written to a temp INI and passed via --load."""
        model = _make_stl(tmp_path)
        out = tmp_path / "out.gcode"
        proc = _make_completed_process()

        with (
            patch("shutil.which", return_value="/usr/bin/prusa-slicer"),
            patch("subprocess.run", return_value=proc) as mock_run,
        ):
            backend = PrusaSlicerBackend()
            result = backend.slice(
                model_path=model,
                output_path=out,
                overrides={"layer_height": "0.15", "infill_density": "20%"},
            )

        # Index 0 = slice invocation; index 1 = get_version() --version call
        cmd = mock_run.call_args_list[0][0][0]
        # At least one --load should point to a print3d_overrides_ temp file
        load_indices = [i for i, v in enumerate(cmd) if v == "--load"]
        override_ini_paths = [
            cmd[i + 1] for i in load_indices if "print3d_overrides_" in cmd[i + 1]
        ]
        assert len(override_ini_paths) == 1
        # The temp file should have been cleaned up after slicing
        assert not Path(override_ini_paths[0]).exists()
        assert result.overrides_applied == {"layer_height": "0.15", "infill_density": "20%"}

    def test_result_contains_expected_metadata(self, tmp_path: Path):
        model = _make_stl(tmp_path)
        out = tmp_path / "out.gcode"
        proc = _make_completed_process(stdout="PrusaSlicer-2.7.1")

        with (
            patch("shutil.which", return_value="/usr/bin/prusa-slicer"),
            patch("subprocess.run", return_value=proc),
        ):
            result = PrusaSlicerBackend().slice(model_path=model, output_path=out)

        assert result.slicer_used == SlicerType.PRUSASLICER
        assert result.gcode_path == str(out)
        assert result.model_path == str(model)

    def test_non_zero_exit_code_raises_slicer_error(self, tmp_path: Path):
        model = _make_stl(tmp_path)
        out = tmp_path / "out.gcode"
        proc = _make_completed_process(returncode=1, stderr="Fatal error: invalid config")

        with (
            patch("shutil.which", return_value="/usr/bin/prusa-slicer"),
            patch("subprocess.run", return_value=proc),
        ):
            with pytest.raises(SlicerError) as exc_info:
                PrusaSlicerBackend().slice(model_path=model, output_path=out)

        assert exc_info.value.slicer == "prusaslicer"
        assert "Fatal error" in exc_info.value.stderr

    def test_timeout_raises_slicer_error(self, tmp_path: Path):
        model = _make_stl(tmp_path)
        out = tmp_path / "out.gcode"

        with (
            patch("shutil.which", return_value="/usr/bin/prusa-slicer"),
            patch(
                "subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd=["prusa-slicer"], timeout=120),
            ),
        ):
            with pytest.raises(SlicerError) as exc_info:
                PrusaSlicerBackend().slice(model_path=model, output_path=out)

        assert "timed out" in str(exc_info.value).lower()

    def test_stderr_non_fatal_collected_as_warning(self, tmp_path: Path):
        """Non-zero-exit stderr content is collected as a warning (not an error)."""
        model = _make_stl(tmp_path)
        out = tmp_path / "out.gcode"
        proc = _make_completed_process(returncode=0, stderr="Warning: config key ignored")

        with (
            patch("shutil.which", return_value="/usr/bin/prusa-slicer"),
            patch("subprocess.run", return_value=proc),
        ):
            result = PrusaSlicerBackend().slice(model_path=model, output_path=out)

        assert len(result.warnings) == 1
        assert "Warning: config key ignored" in result.warnings[0]

    def test_raises_slicer_error_when_not_found_at_slice_time(self, tmp_path: Path):
        """If executable disappears between detect and slice, SlicerError is raised."""
        model = _make_stl(tmp_path)
        out = tmp_path / "out.gcode"

        with patch("shutil.which", return_value=None):
            with pytest.raises(SlicerError) as exc_info:
                PrusaSlicerBackend().slice(model_path=model, output_path=out)

        assert "not found" in str(exc_info.value).lower()


# ===========================================================================
# OrcaSlicerBackend
# ===========================================================================


class TestOrcaSlicerDetect:
    """Tests for OrcaSlicerBackend.detect() and _find_executable()."""

    def test_detect_returns_true_when_orca_slicer_on_path(self):
        with patch(
            "shutil.which",
            side_effect=lambda name: "/usr/bin/orca-slicer" if name == "orca-slicer" else None,
        ):
            assert OrcaSlicerBackend().detect() is True

    def test_detect_returns_true_when_OrcaSlicer_capitalised_on_path(self):
        with patch(
            "shutil.which",
            side_effect=lambda name: "/usr/bin/OrcaSlicer" if name == "OrcaSlicer" else None,
        ):
            assert OrcaSlicerBackend().detect() is True

    def test_detect_returns_false_when_not_on_path(self):
        with patch("shutil.which", return_value=None):
            assert OrcaSlicerBackend().detect() is False


class TestOrcaSlicerSlice:
    """Tests for OrcaSlicerBackend.slice() command construction."""

    def test_basic_command_uses_orca_slicer_executable(self, tmp_path: Path):
        model = _make_stl(tmp_path)
        out = tmp_path / "model_sliced.gcode"
        proc = _make_completed_process()

        with (
            patch("shutil.which", return_value="/usr/bin/orca-slicer"),
            patch("subprocess.run", return_value=proc) as mock_run,
        ):
            OrcaSlicerBackend().slice(model_path=model, output_path=out)

        # Index 0 = slice invocation; index 1 = get_version() --version call
        cmd = mock_run.call_args_list[0][0][0]
        assert cmd[0] == "orca-slicer"
        assert "--export-gcode" in cmd

    def test_3mf_model_accepted(self, tmp_path: Path):
        """OrcaSlicer can also slice .3mf files."""
        model = _make_3mf(tmp_path)
        out = tmp_path / "model_sliced.gcode"
        proc = _make_completed_process()

        with (
            patch("shutil.which", return_value="/usr/bin/orca-slicer"),
            patch("subprocess.run", return_value=proc) as mock_run,
        ):
            OrcaSlicerBackend().slice(model_path=model, output_path=out)

        # Index 0 = slice invocation; index 1 = get_version() --version call
        cmd = mock_run.call_args_list[0][0][0]
        assert str(model) in cmd

    def test_result_slicer_type_is_orcaslicer(self, tmp_path: Path):
        model = _make_stl(tmp_path)
        out = tmp_path / "out.gcode"
        proc = _make_completed_process()

        with (
            patch("shutil.which", return_value="/usr/bin/orca-slicer"),
            patch("subprocess.run", return_value=proc),
        ):
            result = OrcaSlicerBackend().slice(model_path=model, output_path=out)

        assert result.slicer_used == SlicerType.ORCASLICER

    def test_non_zero_exit_code_raises_slicer_error(self, tmp_path: Path):
        model = _make_stl(tmp_path)
        out = tmp_path / "out.gcode"
        proc = _make_completed_process(returncode=2, stderr="OrcaSlicer crashed")

        with (
            patch("shutil.which", return_value="/usr/bin/orca-slicer"),
            patch("subprocess.run", return_value=proc),
        ):
            with pytest.raises(SlicerError) as exc_info:
                OrcaSlicerBackend().slice(model_path=model, output_path=out)

        assert exc_info.value.slicer == "orcaslicer"

    def test_timeout_raises_slicer_error(self, tmp_path: Path):
        model = _make_stl(tmp_path)
        out = tmp_path / "out.gcode"

        with (
            patch("shutil.which", return_value="/usr/bin/orca-slicer"),
            patch(
                "subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd=["orca-slicer"], timeout=120),
            ),
        ):
            with pytest.raises(SlicerError) as exc_info:
                OrcaSlicerBackend().slice(model_path=model, output_path=out)

        assert "timed out" in str(exc_info.value).lower()

    def test_profiles_used_populated_in_result(self, tmp_path: Path):
        model = _make_stl(tmp_path)
        out = tmp_path / "out.gcode"
        proc = _make_completed_process()

        with (
            patch("shutil.which", return_value="/usr/bin/orca-slicer"),
            patch("subprocess.run", return_value=proc),
        ):
            result = OrcaSlicerBackend().slice(
                model_path=model,
                output_path=out,
                printer_profile="/cfg/mk4.ini",
                material_profile="/cfg/pla.ini",
            )

        assert result.profiles_used["printer"] == "/cfg/mk4.ini"
        assert result.profiles_used["material"] == "/cfg/pla.ini"


# ===========================================================================
# slice_model() — public API (auto-detection and validation)
# ===========================================================================


class TestSliceModelFileValidation:
    """Tests for upfront validation in slice_model()."""

    def test_raises_file_not_found_for_missing_model(self, tmp_path: Path):
        missing = tmp_path / "nonexistent.stl"

        with pytest.raises(FileNotFoundError, match="nonexistent.stl"):
            slice_model(missing)

    def test_raises_unsupported_format_for_obj_extension(self, tmp_path: Path):
        """OBJ files are not supported by the slicer backends."""
        obj_file = tmp_path / "model.obj"
        obj_file.write_text("v 0 0 0\n")

        with pytest.raises(UnsupportedFormatError, match=r"\.obj"):
            slice_model(obj_file)

    def test_raises_unsupported_format_for_ply_extension(self, tmp_path: Path):
        ply_file = tmp_path / "model.ply"
        ply_file.write_text("ply\n")

        with pytest.raises(UnsupportedFormatError) as exc_info:
            slice_model(ply_file)

        assert ".ply" in str(exc_info.value)

    @pytest.mark.parametrize("ext", [".stl", ".3mf"])
    def test_supported_extensions_pass_format_check(self, tmp_path: Path, ext: str):
        """Supported extensions should not raise UnsupportedFormatError.
        The error (if any) will come from the backend, not the format check.
        """
        model = tmp_path / f"model{ext}"
        model.write_bytes(b"\x00" * 8)

        # Patch backend to avoid needing a real slicer
        with patch("shutil.which", return_value=None):
            with pytest.raises(CapabilityUnavailable):
                slice_model(model)
            # CapabilityUnavailable, NOT UnsupportedFormatError — format check passed


class TestSliceModelAutoDetection:
    """Tests for slice_model() auto-detection and explicit slicer selection."""

    def test_raises_capability_unavailable_when_no_slicer_found(self, tmp_path: Path):
        """When no slicer is on PATH, CapabilityUnavailable is raised."""
        model = _make_stl(tmp_path)

        with patch("shutil.which", return_value=None):
            with pytest.raises(CapabilityUnavailable) as exc_info:
                slice_model(model)

        assert exc_info.value.capability == "gcode_slicing"

    def test_auto_detection_tries_prusaslicer_first(self, tmp_path: Path):
        """Auto-detection order: PrusaSlicer before OrcaSlicer."""
        model = _make_stl(tmp_path)
        proc = _make_completed_process()
        detected: list[str] = []

        def which_side_effect(name: str) -> str | None:
            detected.append(name)
            # Only PrusaSlicer found
            if name == "prusa-slicer":
                return "/usr/bin/prusa-slicer"
            return None

        with (
            patch("shutil.which", side_effect=which_side_effect),
            patch("subprocess.run", return_value=proc),
        ):
            result = slice_model(model)

        assert result.slicer_used == SlicerType.PRUSASLICER
        # prusa-slicer was in the detection calls
        assert "prusa-slicer" in detected

    def test_auto_detection_falls_back_to_orcaslicer(self, tmp_path: Path):
        """When PrusaSlicer is absent but OrcaSlicer is present, OrcaSlicer is used."""
        model = _make_stl(tmp_path)
        proc = _make_completed_process()

        def which_side_effect(name: str) -> str | None:
            # Only OrcaSlicer on PATH
            if name in ("orca-slicer", "OrcaSlicer"):
                return f"/usr/bin/{name}"
            return None

        with (
            patch("shutil.which", side_effect=which_side_effect),
            patch("subprocess.run", return_value=proc),
        ):
            result = slice_model(model)

        assert result.slicer_used == SlicerType.ORCASLICER

    def test_explicit_slicer_raises_capability_unavailable_when_missing(self, tmp_path: Path):
        """Forcing a specific slicer that is not installed raises CapabilityUnavailable."""
        model = _make_stl(tmp_path)

        with patch("shutil.which", return_value=None):
            with pytest.raises(CapabilityUnavailable) as exc_info:
                slice_model(model, slicer=SlicerType.PRUSASLICER)

        assert exc_info.value.capability == "gcode_slicing"
        assert "prusaslicer" in exc_info.value.provider

    def test_default_output_path_uses_model_stem(self, tmp_path: Path):
        """When output_path is None, output defaults to <stem>_sliced.gcode."""
        model = _make_stl(tmp_path, name="my_part.stl")
        proc = _make_completed_process()

        with (
            patch("shutil.which", return_value="/usr/bin/prusa-slicer"),
            patch("subprocess.run", return_value=proc) as mock_run,
        ):
            slice_model(model)

        # Index 0 = slice invocation; index 1 = get_version() --version call
        cmd = mock_run.call_args_list[0][0][0]
        output_arg = cmd[cmd.index("-o") + 1]
        assert "my_part_sliced.gcode" in output_arg

    def test_explicit_output_path_used_verbatim(self, tmp_path: Path):
        """An explicit output_path is passed directly to the backend."""
        model = _make_stl(tmp_path)
        custom_out = tmp_path / "custom_output.gcode"
        proc = _make_completed_process()

        with (
            patch("shutil.which", return_value="/usr/bin/prusa-slicer"),
            patch("subprocess.run", return_value=proc) as mock_run,
        ):
            result = slice_model(model, output_path=custom_out)

        assert result.gcode_path == str(custom_out)
        # Index 0 = slice invocation; index 1 = get_version() --version call
        cmd = mock_run.call_args_list[0][0][0]
        assert str(custom_out) in cmd

    def test_overrides_forwarded_to_backend(self, tmp_path: Path):
        """**overrides kwargs are forwarded as overrides to the backend."""
        model = _make_stl(tmp_path)
        proc = _make_completed_process()

        with (
            patch("shutil.which", return_value="/usr/bin/prusa-slicer"),
            patch("subprocess.run", return_value=proc),
        ):
            result = slice_model(model, layer_height="0.1", infill_density="30%")

        assert result.overrides_applied == {"layer_height": "0.1", "infill_density": "30%"}

    def test_slice_model_slicer_error_propagates(self, tmp_path: Path):
        """SlicerError from the backend propagates unmodified."""
        model = _make_stl(tmp_path)
        proc = _make_completed_process(returncode=1, stderr="internal error")

        with (
            patch("shutil.which", return_value="/usr/bin/prusa-slicer"),
            patch("subprocess.run", return_value=proc),
        ):
            with pytest.raises(SlicerError):
                slice_model(model)

    def test_capability_unavailable_message_includes_install_hint(self, tmp_path: Path):
        """The CapabilityUnavailable exception carries useful install instructions."""
        model = _make_stl(tmp_path)

        with patch("shutil.which", return_value=None):
            with pytest.raises(CapabilityUnavailable) as exc_info:
                slice_model(model)

        # Should mention at least one slicer to install
        msg = str(exc_info.value)
        assert "PrusaSlicer" in msg or "OrcaSlicer" in msg


# ===========================================================================
# Parameterised: both backends produce consistent output structure
# ===========================================================================


class TestBothBackendsOutputStructure:
    """Parameterised tests asserting SliceResult shape from both backends."""

    @pytest.mark.parametrize(
        "exe_name,backend_cls,expected_type",
        [
            ("prusa-slicer", PrusaSlicerBackend, SlicerType.PRUSASLICER),
            ("orca-slicer", OrcaSlicerBackend, SlicerType.ORCASLICER),
        ],
    )
    def test_result_has_all_required_fields(
        self,
        tmp_path: Path,
        exe_name: str,
        backend_cls: type,
        expected_type: SlicerType,
    ):
        model = _make_stl(tmp_path)
        out = tmp_path / "out.gcode"
        proc = _make_completed_process()

        with (
            patch("shutil.which", return_value=f"/usr/bin/{exe_name}"),
            patch("subprocess.run", return_value=proc),
        ):
            result = backend_cls().slice(model_path=model, output_path=out)

        assert result.gcode_path == str(out)
        assert result.model_path == str(model)
        assert result.slicer_used == expected_type
        assert isinstance(result.profiles_used, dict)
        assert isinstance(result.overrides_applied, dict)
        assert isinstance(result.warnings, list)

    @pytest.mark.parametrize(
        "exe_name,backend_cls",
        [
            ("prusa-slicer", PrusaSlicerBackend),
            ("orca-slicer", OrcaSlicerBackend),
        ],
    )
    def test_non_zero_returncode_always_raises_slicer_error(
        self,
        tmp_path: Path,
        exe_name: str,
        backend_cls: type,
    ):
        model = _make_stl(tmp_path)
        out = tmp_path / "out.gcode"
        proc = _make_completed_process(returncode=1, stderr="crash")

        with (
            patch("shutil.which", return_value=f"/usr/bin/{exe_name}"),
            patch("subprocess.run", return_value=proc),
        ):
            with pytest.raises(SlicerError):
                backend_cls().slice(model_path=model, output_path=out)
