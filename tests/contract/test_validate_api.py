"""Contract tests for the G-code validation and printing public API (F4).

Verifies:
  - parse_gcode / validate_gcode return types have all documented fields
  - Error contracts for missing files, unsupported formats, and empty G-code
  - CapabilityUnavailable raised by slice_model when no slicer is on PATH
  - submit_print always calls validate_gcode before touching the printer
  - All 5 new functions are importable from the top-level package
"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

import pytest

from print3d_skill.exceptions import (
    CapabilityUnavailable,
    GcodeParseError,
    UnsupportedFormatError,
)
from print3d_skill.models.validate import (
    GcodeAnalysis,
    PrintJob,
    ValidationResult,
    ValidationStatus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gcode_analysis_fields() -> set[str]:
    """Return the complete set of documented GcodeAnalysis field names."""
    return {
        "file_path",
        "file_size_bytes",
        "slicer",
        "hotend_temps",
        "bed_temps",
        "chamber_temps",
        "print_speed_mm_s",
        "travel_speed_mm_s",
        "first_layer_speed_mm_s",
        "retraction_distance_mm",
        "retraction_speed_mm_s",
        "z_hop_mm",
        "layer_height_mm",
        "first_layer_height_mm",
        "layer_count",
        "estimated_time_s",
        "estimated_filament_mm",
        "estimated_filament_g",
        "fan_speeds",
        "print_dimensions",
        "line_count",
        "warnings",
    }


def _validation_result_fields() -> set[str]:
    """Return the complete set of documented ValidationResult field names."""
    return {
        "status",
        "gcode_analysis",
        "material_profile",
        "printer_profile",
        "checks",
        "summary",
        "warnings",
        "failures",
        "recommendations",
    }


# ---------------------------------------------------------------------------
# 1. Top-level importability
# ---------------------------------------------------------------------------


class TestF4TopLevelImports:
    """All 5 new functions must be importable from print3d_skill."""

    @pytest.mark.parametrize(
        "func_name",
        ["parse_gcode", "validate_gcode", "slice_model", "list_printers", "submit_print"],
    )
    def test_function_importable_from_package(self, func_name):
        import print3d_skill

        fn = getattr(print3d_skill, func_name, None)
        assert fn is not None, f"{func_name} not found in print3d_skill namespace"
        assert callable(fn), f"{func_name} is not callable"

    def test_parse_gcode_in_all(self):
        import print3d_skill

        assert "parse_gcode" in print3d_skill.__all__

    def test_validate_gcode_in_all(self):
        import print3d_skill

        assert "validate_gcode" in print3d_skill.__all__

    def test_slice_model_in_all(self):
        import print3d_skill

        assert "slice_model" in print3d_skill.__all__

    def test_list_printers_in_all(self):
        import print3d_skill

        assert "list_printers" in print3d_skill.__all__

    def test_submit_print_in_all(self):
        import print3d_skill

        assert "submit_print" in print3d_skill.__all__


# ---------------------------------------------------------------------------
# 2. Function signatures
# ---------------------------------------------------------------------------


class TestParseGcodeSignature:
    """parse_gcode has the documented parameter names."""

    def test_signature_parameters(self):
        from print3d_skill import parse_gcode

        sig = inspect.signature(parse_gcode)
        params = list(sig.parameters.keys())
        assert "gcode_path" in params

    def test_single_required_parameter(self):
        from print3d_skill import parse_gcode

        sig = inspect.signature(parse_gcode)
        # Only one parameter — gcode_path — and it has no default
        assert len(sig.parameters) == 1
        assert sig.parameters["gcode_path"].default is inspect.Parameter.empty


class TestValidateGcodeSignature:
    """validate_gcode has the documented parameter names with optional material/printer."""

    def test_signature_parameters(self):
        from print3d_skill import validate_gcode

        sig = inspect.signature(validate_gcode)
        params = list(sig.parameters.keys())
        assert "gcode_path" in params
        assert "material" in params
        assert "printer" in params

    def test_optional_parameters_default_to_none(self):
        from print3d_skill import validate_gcode

        sig = inspect.signature(validate_gcode)
        assert sig.parameters["material"].default is None
        assert sig.parameters["printer"].default is None


class TestSliceModelSignature:
    """slice_model has the documented parameter names."""

    def test_required_and_optional_params(self):
        from print3d_skill import slice_model

        sig = inspect.signature(slice_model)
        params = list(sig.parameters.keys())
        assert "model_path" in params
        assert "output_path" in params
        assert "slicer" in params
        assert "printer_profile" in params
        assert "material_profile" in params
        assert "quality_preset" in params

    def test_optional_params_default_to_none(self):
        from print3d_skill import slice_model

        sig = inspect.signature(slice_model)
        for name in (
            "output_path",
            "slicer",
            "printer_profile",
            "material_profile",
            "quality_preset",
        ):
            assert sig.parameters[name].default is None, f"Expected {name} to default to None"


class TestSubmitPrintSignature:
    """submit_print has the documented parameter names."""

    def test_required_params(self):
        from print3d_skill import submit_print

        sig = inspect.signature(submit_print)
        params = list(sig.parameters.keys())
        assert "gcode_path" in params
        assert "printer_name" in params

    def test_optional_params(self):
        from print3d_skill import submit_print

        sig = inspect.signature(submit_print)
        assert sig.parameters["material"].default is None
        assert sig.parameters["printer_profile"].default is None


# ---------------------------------------------------------------------------
# 3. GcodeAnalysis return-type field contract
# ---------------------------------------------------------------------------


class TestParseGcodeReturnType:
    """parse_gcode returns a GcodeAnalysis with every documented field."""

    def test_gcode_analysis_is_dataclass(self):
        assert hasattr(GcodeAnalysis, "__dataclass_fields__")

    def test_gcode_analysis_has_all_documented_fields(self):
        declared = set(GcodeAnalysis.__dataclass_fields__.keys())
        expected = _gcode_analysis_fields()
        missing = expected - declared
        assert not missing, f"GcodeAnalysis is missing fields: {missing}"

    def test_parse_gcode_returns_gcode_analysis(self, minimal_gcode_path):
        from print3d_skill import parse_gcode

        result = parse_gcode(str(minimal_gcode_path))

        assert isinstance(result, GcodeAnalysis)

    def test_file_path_field(self, minimal_gcode_path):
        from print3d_skill import parse_gcode

        result = parse_gcode(str(minimal_gcode_path))

        assert isinstance(result.file_path, str)
        assert result.file_path != ""

    def test_file_size_bytes_field(self, minimal_gcode_path):
        from print3d_skill import parse_gcode

        result = parse_gcode(str(minimal_gcode_path))

        assert isinstance(result.file_size_bytes, int)
        assert result.file_size_bytes > 0

    def test_slicer_field_is_str_or_none(self, minimal_gcode_path):
        from print3d_skill import parse_gcode

        result = parse_gcode(str(minimal_gcode_path))

        assert result.slicer is None or isinstance(result.slicer, str)

    def test_hotend_temps_is_list(self, minimal_gcode_path):
        from print3d_skill import parse_gcode

        result = parse_gcode(str(minimal_gcode_path))

        assert isinstance(result.hotend_temps, list)

    def test_bed_temps_is_list(self, minimal_gcode_path):
        from print3d_skill import parse_gcode

        result = parse_gcode(str(minimal_gcode_path))

        assert isinstance(result.bed_temps, list)

    def test_chamber_temps_is_list(self, minimal_gcode_path):
        from print3d_skill import parse_gcode

        result = parse_gcode(str(minimal_gcode_path))

        assert isinstance(result.chamber_temps, list)

    def test_fan_speeds_is_list(self, minimal_gcode_path):
        from print3d_skill import parse_gcode

        result = parse_gcode(str(minimal_gcode_path))

        assert isinstance(result.fan_speeds, list)

    def test_line_count_is_positive_int(self, minimal_gcode_path):
        from print3d_skill import parse_gcode

        result = parse_gcode(str(minimal_gcode_path))

        assert isinstance(result.line_count, int)
        assert result.line_count > 0

    def test_warnings_is_list(self, minimal_gcode_path):
        from print3d_skill import parse_gcode

        result = parse_gcode(str(minimal_gcode_path))

        assert isinstance(result.warnings, list)

    def test_optional_numeric_fields_are_float_or_none(self, minimal_gcode_path):
        from print3d_skill import parse_gcode

        result = parse_gcode(str(minimal_gcode_path))

        optional_float_fields = [
            "print_speed_mm_s",
            "travel_speed_mm_s",
            "first_layer_speed_mm_s",
            "retraction_distance_mm",
            "retraction_speed_mm_s",
            "z_hop_mm",
            "layer_height_mm",
            "first_layer_height_mm",
            "estimated_time_s",
            "estimated_filament_mm",
            "estimated_filament_g",
        ]
        for field in optional_float_fields:
            value = getattr(result, field)
            assert value is None or isinstance(value, (int, float)), (
                f"Field {field!r} expected float | None, got {type(value)}"
            )

    def test_layer_count_is_int_or_none(self, minimal_gcode_path):
        from print3d_skill import parse_gcode

        result = parse_gcode(str(minimal_gcode_path))

        assert result.layer_count is None or isinstance(result.layer_count, int)

    def test_print_dimensions_field_type(self, minimal_gcode_path):
        from print3d_skill import parse_gcode
        from print3d_skill.models.validate import PrintDimensions

        result = parse_gcode(str(minimal_gcode_path))

        assert result.print_dimensions is None or isinstance(
            result.print_dimensions, PrintDimensions
        )

    def test_parse_gcode_with_prusaslicer_fixture(self, prusaslicer_gcode_path):
        """PrusaSlicer fixture file is detected as such and slicer field is set."""
        from print3d_skill import parse_gcode

        if not prusaslicer_gcode_path.exists():
            pytest.skip("PrusaSlicer fixture not present")

        result = parse_gcode(str(prusaslicer_gcode_path))

        assert isinstance(result, GcodeAnalysis)
        # PrusaSlicer G-code should identify the slicer
        assert result.slicer is not None
        assert "prusa" in result.slicer.lower()


# ---------------------------------------------------------------------------
# 4. ValidationResult return-type field contract
# ---------------------------------------------------------------------------


class TestValidateGcodeReturnType:
    """validate_gcode returns a ValidationResult with every documented field."""

    def test_validation_result_is_dataclass(self):
        assert hasattr(ValidationResult, "__dataclass_fields__")

    def test_validation_result_has_all_documented_fields(self):
        declared = set(ValidationResult.__dataclass_fields__.keys())
        expected = _validation_result_fields()
        missing = expected - declared
        assert not missing, f"ValidationResult is missing fields: {missing}"

    def test_validate_gcode_returns_validation_result(self, minimal_gcode_path):
        from print3d_skill import validate_gcode

        result = validate_gcode(str(minimal_gcode_path))

        assert isinstance(result, ValidationResult)

    def test_status_field_is_validation_status_enum(self, minimal_gcode_path):
        from print3d_skill import validate_gcode

        result = validate_gcode(str(minimal_gcode_path))

        assert isinstance(result.status, ValidationStatus)

    def test_gcode_analysis_field_is_gcode_analysis(self, minimal_gcode_path):
        from print3d_skill import validate_gcode

        result = validate_gcode(str(minimal_gcode_path))

        assert isinstance(result.gcode_analysis, GcodeAnalysis)

    def test_material_profile_field_is_str_or_none(self, minimal_gcode_path):
        from print3d_skill import validate_gcode

        result = validate_gcode(str(minimal_gcode_path))

        assert result.material_profile is None or isinstance(result.material_profile, str)

    def test_printer_profile_field_is_str_or_none(self, minimal_gcode_path):
        from print3d_skill import validate_gcode

        result = validate_gcode(str(minimal_gcode_path))

        assert result.printer_profile is None or isinstance(result.printer_profile, str)

    def test_checks_field_is_list(self, minimal_gcode_path):
        from print3d_skill import validate_gcode

        result = validate_gcode(str(minimal_gcode_path))

        assert isinstance(result.checks, list)

    def test_summary_field_is_str(self, minimal_gcode_path):
        from print3d_skill import validate_gcode

        result = validate_gcode(str(minimal_gcode_path))

        assert isinstance(result.summary, str)

    def test_warnings_field_is_list(self, minimal_gcode_path):
        from print3d_skill import validate_gcode

        result = validate_gcode(str(minimal_gcode_path))

        assert isinstance(result.warnings, list)

    def test_failures_field_is_list(self, minimal_gcode_path):
        from print3d_skill import validate_gcode

        result = validate_gcode(str(minimal_gcode_path))

        assert isinstance(result.failures, list)

    def test_recommendations_field_is_list(self, minimal_gcode_path):
        from print3d_skill import validate_gcode

        result = validate_gcode(str(minimal_gcode_path))

        assert isinstance(result.recommendations, list)

    def test_validate_with_known_material_adds_warning_for_unknown(self, minimal_gcode_path):
        """An unknown material name yields a warning, not an exception."""
        from print3d_skill import validate_gcode

        result = validate_gcode(str(minimal_gcode_path), material="NONEXISTENT_MATERIAL")

        assert isinstance(result, ValidationResult)
        # A warning about the missing profile must appear
        warning_text = " ".join(result.warnings).lower()
        assert "nonexistent_material" in warning_text or "not found" in warning_text

    def test_validate_with_known_printer_adds_warning_for_unknown(self, minimal_gcode_path):
        """An unknown printer name yields a warning, not an exception."""
        from print3d_skill import validate_gcode

        result = validate_gcode(str(minimal_gcode_path), printer="NO_SUCH_PRINTER")

        assert isinstance(result, ValidationResult)
        warning_text = " ".join(result.warnings).lower()
        assert "no_such_printer" in warning_text or "not found" in warning_text


# ---------------------------------------------------------------------------
# 5. Error contracts — FileNotFoundError
# ---------------------------------------------------------------------------


class TestParseGcodeFileNotFound:
    """parse_gcode raises FileNotFoundError for a path that does not exist."""

    def test_missing_gcode_file(self, tmp_path):
        from print3d_skill import parse_gcode

        missing = tmp_path / "does_not_exist.gcode"

        with pytest.raises(FileNotFoundError):
            parse_gcode(str(missing))

    def test_error_message_contains_path(self, tmp_path):
        from print3d_skill import parse_gcode

        missing = tmp_path / "missing.gcode"

        with pytest.raises(FileNotFoundError, match="missing.gcode"):
            parse_gcode(str(missing))


class TestValidateGcodeFileNotFound:
    """validate_gcode propagates FileNotFoundError from parse_gcode."""

    def test_missing_gcode_file(self, tmp_path):
        from print3d_skill import validate_gcode

        missing = tmp_path / "does_not_exist.gcode"

        with pytest.raises(FileNotFoundError):
            validate_gcode(str(missing))


# ---------------------------------------------------------------------------
# 6. Error contracts — UnsupportedFormatError
# ---------------------------------------------------------------------------


class TestParseGcodeUnsupportedFormat:
    """parse_gcode raises UnsupportedFormatError for non-.gcode extensions."""

    @pytest.mark.parametrize("filename", ["model.stl", "data.txt", "output.csv", "file"])
    def test_wrong_extension_raises_unsupported_format(self, tmp_path, filename):
        from print3d_skill import parse_gcode

        # File must exist so we get past the FileNotFoundError check
        bad_file = tmp_path / filename
        bad_file.write_text("; fake content")

        with pytest.raises(UnsupportedFormatError):
            parse_gcode(str(bad_file))

    def test_error_is_subclass_of_print3d_skill_error(self, tmp_path):
        from print3d_skill import parse_gcode
        from print3d_skill.exceptions import Print3DSkillError

        bad_file = tmp_path / "model.stl"
        bad_file.write_text("; fake")

        with pytest.raises(Print3DSkillError):
            parse_gcode(str(bad_file))


class TestValidateGcodeUnsupportedFormat:
    """validate_gcode propagates UnsupportedFormatError from parse_gcode."""

    def test_wrong_extension_raises_unsupported_format(self, tmp_path):
        from print3d_skill import validate_gcode

        bad_file = tmp_path / "model.stl"
        bad_file.write_text("; fake content")

        with pytest.raises(UnsupportedFormatError):
            validate_gcode(str(bad_file))


# ---------------------------------------------------------------------------
# 7. Error contracts — GcodeParseError
# ---------------------------------------------------------------------------


class TestParseGcodeEmptyFile:
    """parse_gcode raises GcodeParseError for an empty G-code file."""

    def test_empty_gcode_file(self, tmp_path):
        from print3d_skill import parse_gcode

        empty = tmp_path / "empty.gcode"
        empty.write_text("")

        with pytest.raises(GcodeParseError):
            parse_gcode(str(empty))

    def test_error_is_subclass_of_print3d_skill_error(self, tmp_path):
        from print3d_skill import parse_gcode
        from print3d_skill.exceptions import Print3DSkillError

        empty = tmp_path / "empty.gcode"
        empty.write_text("")

        with pytest.raises(Print3DSkillError):
            parse_gcode(str(empty))

    def test_truly_zero_byte_file_raises_gcode_parse_error(self, tmp_path):
        """A file with zero bytes (os.path.getsize == 0) raises GcodeParseError."""
        from print3d_skill import parse_gcode

        zero_byte = tmp_path / "zero_byte.gcode"
        zero_byte.write_bytes(b"")

        with pytest.raises(GcodeParseError):
            parse_gcode(str(zero_byte))


# ---------------------------------------------------------------------------
# 8. CapabilityUnavailable for slice_model when no slicer is installed
# ---------------------------------------------------------------------------


class TestSliceModelCapabilityUnavailable:
    """slice_model raises CapabilityUnavailable when no slicer CLI is on PATH."""

    def test_no_slicer_on_path_raises_capability_unavailable(self, tmp_path):
        from print3d_skill import slice_model

        # Create a valid-looking STL file so file checks pass
        stl_file = tmp_path / "model.stl"
        stl_file.write_bytes(b"\x00" * 84 + b"\x00" * 50 * 50)  # minimal binary STL

        # Patch shutil.which in both slicer backend modules to simulate no slicer
        with patch("shutil.which", return_value=None):
            with pytest.raises(CapabilityUnavailable) as exc_info:
                slice_model(str(stl_file))

        assert exc_info.value.capability == "gcode_slicing"

    def test_capability_unavailable_has_install_instructions(self, tmp_path):
        from print3d_skill import slice_model

        stl_file = tmp_path / "model.stl"
        stl_file.write_bytes(b"\x00" * 84 + b"\x00" * 50 * 50)

        with patch("shutil.which", return_value=None):
            with pytest.raises(CapabilityUnavailable) as exc_info:
                slice_model(str(stl_file))

        # install_instructions must be a non-empty string
        assert isinstance(exc_info.value.install_instructions, str)
        assert exc_info.value.install_instructions != ""

    def test_capability_unavailable_is_subclass_of_print3d_skill_error(self, tmp_path):
        from print3d_skill import slice_model
        from print3d_skill.exceptions import Print3DSkillError

        stl_file = tmp_path / "model.stl"
        stl_file.write_bytes(b"\x00" * 84 + b"\x00" * 50 * 50)

        with patch("shutil.which", return_value=None):
            with pytest.raises(Print3DSkillError):
                slice_model(str(stl_file))

    def test_slice_model_file_not_found_before_capability_check(self, tmp_path):
        """FileNotFoundError is raised before CapabilityUnavailable."""
        from print3d_skill import slice_model

        missing = tmp_path / "nonexistent.stl"

        with patch("shutil.which", return_value=None):
            with pytest.raises(FileNotFoundError):
                slice_model(str(missing))

    def test_slice_model_unsupported_format_before_capability_check(self, tmp_path):
        """UnsupportedFormatError is raised before CapabilityUnavailable."""
        from print3d_skill import slice_model

        bad_file = tmp_path / "model.obj"
        bad_file.write_text("v 0 0 0")

        with patch("shutil.which", return_value=None):
            with pytest.raises(UnsupportedFormatError):
                slice_model(str(bad_file))


# ---------------------------------------------------------------------------
# 9. submit_print validates before touching the printer
# ---------------------------------------------------------------------------


class TestSubmitPrintValidatesFirst:
    """submit_print always calls validate_gcode before any printer interaction."""

    def _make_passing_validation_result(self, gcode_path: str) -> ValidationResult:
        """Build a ValidationResult stub that passes."""
        analysis = GcodeAnalysis(
            file_path=gcode_path,
            file_size_bytes=100,
            line_count=10,
        )
        return ValidationResult(
            status=ValidationStatus.PASS,
            gcode_analysis=analysis,
            summary="All checks passed",
        )

    def test_validate_gcode_called_before_printer_connect(self, minimal_gcode_path, tmp_path):
        """validate_gcode must be invoked; printer backend must NOT be called first."""
        from print3d_skill import submit_print

        gcode_path = str(minimal_gcode_path)
        validation_result = self._make_passing_validation_result(gcode_path)

        # Track call order
        call_order: list[str] = []

        # Patch validate_gcode inside the printing module (where it's imported)
        def fake_validate_gcode(gcode_path, material=None, printer=None):
            call_order.append("validate_gcode")
            return validation_result

        # A mock printer connection and backend
        mock_conn = MagicMock()
        mock_conn.name = "test-printer"

        mock_backend = MagicMock()

        def fake_connect():
            call_order.append("printer_connect")
            return True

        mock_backend.connect.side_effect = fake_connect
        mock_backend.status.return_value = MagicMock(status=MagicMock(value="idle"))
        # Make status.status compare equal to PrinterStatus.ERROR — set it to
        # something that is NOT the error sentinel so no PrinterError is raised
        from print3d_skill.models.validate import PrinterStatus

        mock_backend.status.return_value.status = PrinterStatus.IDLE
        mock_backend.upload.return_value = True
        mock_backend.start_print.return_value = True

        with (
            patch(
                "print3d_skill.validate.validate_gcode",
                side_effect=fake_validate_gcode,
            ),
            patch(
                "print3d_skill.printing.config.load_printer_config",
                return_value=[mock_conn],
            ),
            patch(
                "print3d_skill.printing._create_backend",
                return_value=mock_backend,
            ),
        ):
            submit_print(
                gcode_path=gcode_path,
                printer_name="test-printer",
            )

        # validate_gcode must appear before printer_connect in the call order
        assert "validate_gcode" in call_order, "validate_gcode was never called"
        assert "printer_connect" in call_order, "printer connect was never called"
        validate_idx = call_order.index("validate_gcode")
        connect_idx = call_order.index("printer_connect")
        assert validate_idx < connect_idx, (
            f"validate_gcode (pos {validate_idx}) must come before "
            f"printer_connect (pos {connect_idx})"
        )

    def test_submit_print_raises_validation_error_on_fail(self, minimal_gcode_path):
        """If validation returns FAIL, ValidationError is raised immediately."""
        from print3d_skill import submit_print
        from print3d_skill.exceptions import ValidationError

        gcode_path = str(minimal_gcode_path)
        failing_result = ValidationResult(
            status=ValidationStatus.FAIL,
            gcode_analysis=GcodeAnalysis(file_path=gcode_path, line_count=1),
            failures=["Hotend temperature 300 °C exceeds material maximum"],
            summary="Validation failed",
        )

        mock_backend = MagicMock()

        with (
            patch(
                "print3d_skill.validate.validate_gcode",
                return_value=failing_result,
            ),
            patch(
                "print3d_skill.printing.config.load_printer_config",
                return_value=[MagicMock(name="test-printer")],
            ),
            patch(
                "print3d_skill.printing._create_backend",
                return_value=mock_backend,
            ),
        ):
            with pytest.raises(ValidationError):
                submit_print(
                    gcode_path=gcode_path,
                    printer_name="test-printer",
                )

        # Printer must not have been touched at all
        mock_backend.connect.assert_not_called()
        mock_backend.upload.assert_not_called()
        mock_backend.start_print.assert_not_called()

    def test_submit_print_returns_print_job(self, minimal_gcode_path):
        """On success, submit_print returns a PrintJob with all documented fields."""
        from print3d_skill import submit_print

        gcode_path = str(minimal_gcode_path)
        passing_result = self._make_passing_validation_result(gcode_path)

        mock_conn = MagicMock()
        mock_conn.name = "test-printer"

        from print3d_skill.models.validate import PrinterStatus

        mock_backend = MagicMock()
        mock_backend.status.return_value.status = PrinterStatus.IDLE
        mock_backend.upload.return_value = True
        mock_backend.start_print.return_value = True

        with (
            patch(
                "print3d_skill.validate.validate_gcode",
                return_value=passing_result,
            ),
            patch(
                "print3d_skill.printing.config.load_printer_config",
                return_value=[mock_conn],
            ),
            patch(
                "print3d_skill.printing._create_backend",
                return_value=mock_backend,
            ),
        ):
            job = submit_print(
                gcode_path=gcode_path,
                printer_name="test-printer",
            )

        assert isinstance(job, PrintJob)
        assert isinstance(job.printer_name, str)
        assert isinstance(job.gcode_path, str)
        assert isinstance(job.validation_result, ValidationResult)
        assert isinstance(job.submitted, bool)
        assert isinstance(job.message, str)
        assert job.submitted is True

    def test_submit_print_file_not_found_skips_validation(self, tmp_path):
        """FileNotFoundError is raised before validate_gcode is called.

        The validate_gcode import inside submit_print is a local import, so we
        patch it at its definition site. The file-existence check runs first,
        raising FileNotFoundError before the import can execute.
        """
        from print3d_skill import submit_print

        missing = tmp_path / "missing.gcode"

        with patch("print3d_skill.validate.validate_gcode") as mock_validate:
            with pytest.raises(FileNotFoundError):
                submit_print(
                    gcode_path=str(missing),
                    printer_name="test-printer",
                )

        mock_validate.assert_not_called()


# ---------------------------------------------------------------------------
# 10. Model dataclass structure contracts
# ---------------------------------------------------------------------------


class TestValidateModels:
    """The validate-related model dataclasses have all their expected fields."""

    @pytest.mark.parametrize(
        "type_name,expected_fields",
        [
            (
                "GcodeAnalysis",
                _gcode_analysis_fields(),
            ),
            (
                "ValidationResult",
                _validation_result_fields(),
            ),
        ],
    )
    def test_dataclass_has_required_fields(self, type_name, expected_fields):
        from print3d_skill import models

        cls = getattr(models, type_name, None)
        if cls is None:
            from print3d_skill.models import validate as validate_models

            cls = getattr(validate_models, type_name)
        declared = set(cls.__dataclass_fields__.keys())
        missing = expected_fields - declared
        assert not missing, f"{type_name} is missing fields: {missing}"

    def test_validation_check_dataclass_exists(self):
        from print3d_skill.models.validate import ValidationCheck

        assert hasattr(ValidationCheck, "__dataclass_fields__")
        fields = set(ValidationCheck.__dataclass_fields__.keys())
        assert "category" in fields
        assert "name" in fields
        assert "severity" in fields
        assert "message" in fields

    def test_print_job_dataclass_exists(self):
        assert hasattr(PrintJob, "__dataclass_fields__")
        fields = set(PrintJob.__dataclass_fields__.keys())
        assert "printer_name" in fields
        assert "gcode_path" in fields
        assert "validation_result" in fields
        assert "submitted" in fields
        assert "message" in fields


# ---------------------------------------------------------------------------
# 11. New exception classes exist and inherit from Print3DSkillError
# ---------------------------------------------------------------------------


class TestF4Exceptions:
    """F4-specific exceptions exist and inherit from Print3DSkillError."""

    @pytest.mark.parametrize(
        "exc_name",
        ["GcodeParseError", "SlicerError", "ValidationError", "PrinterError"],
    )
    def test_exception_inherits_from_base(self, exc_name):
        from print3d_skill import exceptions
        from print3d_skill.exceptions import Print3DSkillError

        exc_class = getattr(exceptions, exc_name)
        assert issubclass(exc_class, Print3DSkillError), (
            f"{exc_name} must inherit from Print3DSkillError"
        )

    def test_slicer_error_stores_slicer_attribute(self):
        from print3d_skill.exceptions import SlicerError

        exc = SlicerError("prusaslicer", stderr="some error", message="failed")
        assert exc.slicer == "prusaslicer"
        assert isinstance(exc.stderr, str)

    def test_validation_error_stores_validation_result(self):
        from print3d_skill.exceptions import ValidationError

        result = ValidationResult(status=ValidationStatus.FAIL)
        exc = ValidationError("failed", validation_result=result)
        assert exc.validation_result is result

    def test_printer_error_stores_printer_name(self):
        from print3d_skill.exceptions import PrinterError

        exc = PrinterError("my-printer", "connection refused")
        assert exc.printer_name == "my-printer"

    def test_capability_unavailable_stores_all_attributes(self):
        exc = CapabilityUnavailable(
            capability="gcode_slicing",
            provider="prusaslicer",
            install_instructions="brew install prusa-slicer",
        )
        assert exc.capability == "gcode_slicing"
        assert exc.provider == "prusaslicer"
        assert exc.install_instructions == "brew install prusa-slicer"
