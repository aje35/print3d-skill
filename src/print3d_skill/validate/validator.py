"""Settings validation engine that runs checks and aggregates results."""

from __future__ import annotations

from print3d_skill.models.validate import (
    CheckSeverity,
    GcodeAnalysis,
    MaterialProfile,
    PrinterProfile,
    ValidationCheck,
    ValidationResult,
    ValidationStatus,
)


def validate_gcode_settings(
    analysis: GcodeAnalysis,
    material_profile: MaterialProfile | None = None,
    printer_profile: PrinterProfile | None = None,
) -> ValidationResult:
    """Run all applicable validation checks and aggregate results.

    Args:
        analysis: Parsed G-code analysis.
        material_profile: Material profile for temperature/speed checks (or None).
        printer_profile: Printer profile for build volume/retraction checks (or None).

    Returns:
        ValidationResult with overall status and individual check details.
    """
    from print3d_skill.validate.checks import (
        check_bed_temperature,
        check_build_volume,
        check_enclosure,
        check_first_layer,
        check_hotend_temperature,
        check_print_speed,
        check_print_time,
        check_retraction,
    )

    checks: list[ValidationCheck] = []

    # Always run time estimate check
    checks.append(check_print_time(analysis))

    # Material-specific checks
    if material_profile is not None:
        checks.append(check_hotend_temperature(analysis, material_profile))
        checks.append(check_bed_temperature(analysis, material_profile))
        checks.append(check_print_speed(analysis, material_profile))
        checks.append(check_first_layer(analysis, material_profile))

    # Printer-specific checks
    if printer_profile is not None:
        checks.append(check_retraction(analysis, printer_profile))
        checks.append(check_build_volume(analysis, printer_profile))

    # Combined checks (need both profiles)
    if material_profile is not None and printer_profile is not None:
        checks.append(check_enclosure(analysis, material_profile, printer_profile))

    # Aggregate results
    failures = [c for c in checks if c.severity == CheckSeverity.FAIL]
    warnings = [c for c in checks if c.severity == CheckSeverity.WARN]

    if failures:
        status = ValidationStatus.FAIL
    elif warnings:
        status = ValidationStatus.WARN
    else:
        status = ValidationStatus.PASS

    failure_msgs = [f"[{c.name}] {c.message}" for c in failures]
    warning_msgs = [f"[{c.name}] {c.message}" for c in warnings]
    recommendations = [c.recommendation for c in checks if c.recommendation]

    # Build summary
    total = len(checks)
    pass_count = sum(1 for c in checks if c.severity == CheckSeverity.PASS)
    summary_parts = [f"{pass_count}/{total} checks passed"]
    if warnings:
        summary_parts.append(f"{len(warnings)} warning(s)")
    if failures:
        summary_parts.append(f"{len(failures)} failure(s)")
    summary = ". ".join(summary_parts) + "."

    return ValidationResult(
        status=status,
        gcode_analysis=analysis,
        material_profile=material_profile.name if material_profile else None,
        printer_profile=printer_profile.name if printer_profile else None,
        checks=checks,
        summary=summary,
        warnings=warning_msgs,
        failures=failure_msgs,
        recommendations=recommendations,
    )
