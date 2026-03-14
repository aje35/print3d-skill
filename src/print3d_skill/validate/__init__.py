"""G-code parsing and validation (core tier).

Public API:
    parse_gcode(gcode_path) -> GcodeAnalysis
    validate_gcode(gcode_path, material, printer) -> ValidationResult
"""

from __future__ import annotations

import os

from print3d_skill.exceptions import GcodeParseError as GcodeParseError
from print3d_skill.exceptions import UnsupportedFormatError
from print3d_skill.models.validate import GcodeAnalysis, ValidationResult


def parse_gcode(gcode_path: str) -> GcodeAnalysis:
    """Parse a G-code file and extract structured parameters.

    Args:
        gcode_path: Path to G-code file. Must exist and be readable.

    Returns:
        GcodeAnalysis dataclass with all extracted parameters.

    Raises:
        FileNotFoundError: File does not exist.
        UnsupportedFormatError: File is not a G-code file (wrong extension).
        GcodeParseError: File is corrupted or empty.
    """
    if not os.path.exists(gcode_path):
        raise FileNotFoundError(f"G-code file not found: {gcode_path}")

    if not gcode_path.lower().endswith(".gcode"):
        raise UnsupportedFormatError(
            f"Not a G-code file (expected .gcode extension): {gcode_path}"
        )

    from print3d_skill.validate.parser import parse_gcode_file

    return parse_gcode_file(gcode_path)


def validate_gcode(
    gcode_path: str,
    material: str | None = None,
    printer: str | None = None,
) -> ValidationResult:
    """Validate G-code settings against material and printer profiles.

    Args:
        gcode_path: Path to G-code file.
        material: Material name (e.g., "PLA", "PETG"). If None, material checks skipped.
        printer: Printer profile name. If None, printer checks skipped.

    Returns:
        ValidationResult with status (PASS/WARN/FAIL), checks, and recommendations.

    Raises:
        FileNotFoundError: G-code file does not exist.
        UnsupportedFormatError: Not a G-code file.
        GcodeParseError: File is corrupted or empty.
    """
    analysis = parse_gcode(gcode_path)

    from print3d_skill.validate.profiles import (
        load_material_profile,
        load_printer_profile,
    )
    from print3d_skill.validate.validator import validate_gcode_settings

    material_profile = None
    printer_profile = None
    extra_warnings: list[str] = []

    if material is not None:
        material_profile = load_material_profile(material)
        if material_profile is None:
            extra_warnings.append(
                f"Material profile '{material}' not found — material checks skipped"
            )

    if printer is not None:
        printer_profile = load_printer_profile(printer)
        if printer_profile is None:
            extra_warnings.append(
                f"Printer profile '{printer}' not found — printer checks skipped"
            )

    result = validate_gcode_settings(analysis, material_profile, printer_profile)

    if extra_warnings:
        result.warnings.extend(extra_warnings)

    return result
