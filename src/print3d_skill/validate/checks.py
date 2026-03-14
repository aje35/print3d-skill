"""Individual G-code validation check functions.

Each function takes a GcodeAnalysis and a profile (material or printer),
returning a ValidationCheck with PASS, WARN, or FAIL severity.

Severity rules (from R6):
- FAIL: physical impossibility or unsafe (blocks printing)
- WARN: quality risk (advisory, allows printing)
- PASS: within expected range
"""

from __future__ import annotations

from print3d_skill.models.validate import (
    CheckCategory,
    CheckSeverity,
    ExtruderType,
    GcodeAnalysis,
    MaterialProfile,
    PrinterProfile,
    ValidationCheck,
)


def check_hotend_temperature(
    analysis: GcodeAnalysis,
    material: MaterialProfile,
) -> ValidationCheck:
    """Check hotend temperature against material profile range.

    Uses the highest target hotend temp found in the G-code.
    WARN if outside the material's recommended range.
    """
    if not analysis.hotend_temps:
        return ValidationCheck(
            category=CheckCategory.TEMPERATURE,
            name="hotend_temperature",
            severity=CheckSeverity.PASS,
            actual_value="no hotend temps found",
            expected_range=f"{material.hotend_temp_min_c}-{material.hotend_temp_max_c}C",
            message="No hotend temperature commands found in G-code",
            recommendation="",
        )

    highest_temp = max(cmd.target_temp_c for cmd in analysis.hotend_temps)

    if highest_temp > material.hotend_temp_max_c:
        return ValidationCheck(
            category=CheckCategory.TEMPERATURE,
            name="hotend_temperature",
            severity=CheckSeverity.WARN,
            actual_value=f"{highest_temp}C",
            expected_range=f"{material.hotend_temp_min_c}-{material.hotend_temp_max_c}C",
            message=(
                f"Hotend temperature {highest_temp}C exceeds "
                f"recommended max {material.hotend_temp_max_c}C for {material.name}"
            ),
            recommendation=(f"Lower hotend temperature to {material.hotend_temp_max_c}C or below"),
        )

    if highest_temp < material.hotend_temp_min_c:
        return ValidationCheck(
            category=CheckCategory.TEMPERATURE,
            name="hotend_temperature",
            severity=CheckSeverity.WARN,
            actual_value=f"{highest_temp}C",
            expected_range=f"{material.hotend_temp_min_c}-{material.hotend_temp_max_c}C",
            message=(
                f"Hotend temperature {highest_temp}C is below "
                f"recommended min {material.hotend_temp_min_c}C for {material.name}"
            ),
            recommendation=(f"Raise hotend temperature to at least {material.hotend_temp_min_c}C"),
        )

    return ValidationCheck(
        category=CheckCategory.TEMPERATURE,
        name="hotend_temperature",
        severity=CheckSeverity.PASS,
        actual_value=f"{highest_temp}C",
        expected_range=f"{material.hotend_temp_min_c}-{material.hotend_temp_max_c}C",
        message=f"Hotend temperature {highest_temp}C is within recommended range",
        recommendation="",
    )


def check_bed_temperature(
    analysis: GcodeAnalysis,
    material: MaterialProfile,
) -> ValidationCheck:
    """Check bed temperature against material profile range.

    Uses the highest target bed temp found in the G-code.
    WARN if outside the material's recommended range.
    """
    if not analysis.bed_temps:
        return ValidationCheck(
            category=CheckCategory.TEMPERATURE,
            name="bed_temperature",
            severity=CheckSeverity.PASS,
            actual_value="no bed temps found",
            expected_range=f"{material.bed_temp_min_c}-{material.bed_temp_max_c}C",
            message="No bed temperature commands found in G-code",
            recommendation="",
        )

    highest_temp = max(cmd.target_temp_c for cmd in analysis.bed_temps)

    if highest_temp > material.bed_temp_max_c:
        return ValidationCheck(
            category=CheckCategory.TEMPERATURE,
            name="bed_temperature",
            severity=CheckSeverity.WARN,
            actual_value=f"{highest_temp}C",
            expected_range=f"{material.bed_temp_min_c}-{material.bed_temp_max_c}C",
            message=(
                f"Bed temperature {highest_temp}C exceeds "
                f"recommended max {material.bed_temp_max_c}C for {material.name}"
            ),
            recommendation=(f"Lower bed temperature to {material.bed_temp_max_c}C or below"),
        )

    if highest_temp < material.bed_temp_min_c:
        return ValidationCheck(
            category=CheckCategory.TEMPERATURE,
            name="bed_temperature",
            severity=CheckSeverity.WARN,
            actual_value=f"{highest_temp}C",
            expected_range=f"{material.bed_temp_min_c}-{material.bed_temp_max_c}C",
            message=(
                f"Bed temperature {highest_temp}C is below "
                f"recommended min {material.bed_temp_min_c}C for {material.name}"
            ),
            recommendation=(f"Raise bed temperature to at least {material.bed_temp_min_c}C"),
        )

    return ValidationCheck(
        category=CheckCategory.TEMPERATURE,
        name="bed_temperature",
        severity=CheckSeverity.PASS,
        actual_value=f"{highest_temp}C",
        expected_range=f"{material.bed_temp_min_c}-{material.bed_temp_max_c}C",
        message=f"Bed temperature {highest_temp}C is within recommended range",
        recommendation="",
    )


def check_print_speed(
    analysis: GcodeAnalysis,
    material: MaterialProfile,
) -> ValidationCheck:
    """Check print speed against material profile range.

    WARN if outside the material's recommended speed range.
    """
    if analysis.print_speed_mm_s is None:
        return ValidationCheck(
            category=CheckCategory.SPEED,
            name="print_speed",
            severity=CheckSeverity.PASS,
            actual_value="not detected",
            expected_range=f"{material.speed_min_mm_s}-{material.speed_max_mm_s}mm/s",
            message="Print speed not detected in G-code",
            recommendation="",
        )

    speed = analysis.print_speed_mm_s

    if speed > material.speed_max_mm_s:
        return ValidationCheck(
            category=CheckCategory.SPEED,
            name="print_speed",
            severity=CheckSeverity.WARN,
            actual_value=f"{speed}mm/s",
            expected_range=f"{material.speed_min_mm_s}-{material.speed_max_mm_s}mm/s",
            message=(
                f"Print speed {speed}mm/s exceeds recommended max "
                f"{material.speed_max_mm_s}mm/s for {material.name}"
            ),
            recommendation=(f"Reduce print speed to {material.speed_max_mm_s}mm/s or below"),
        )

    if speed < material.speed_min_mm_s:
        return ValidationCheck(
            category=CheckCategory.SPEED,
            name="print_speed",
            severity=CheckSeverity.WARN,
            actual_value=f"{speed}mm/s",
            expected_range=f"{material.speed_min_mm_s}-{material.speed_max_mm_s}mm/s",
            message=(
                f"Print speed {speed}mm/s is below recommended min "
                f"{material.speed_min_mm_s}mm/s for {material.name}"
            ),
            recommendation=(f"Increase print speed to at least {material.speed_min_mm_s}mm/s"),
        )

    return ValidationCheck(
        category=CheckCategory.SPEED,
        name="print_speed",
        severity=CheckSeverity.PASS,
        actual_value=f"{speed}mm/s",
        expected_range=f"{material.speed_min_mm_s}-{material.speed_max_mm_s}mm/s",
        message=f"Print speed {speed}mm/s is within recommended range",
        recommendation="",
    )


def check_retraction(
    analysis: GcodeAnalysis,
    printer: PrinterProfile,
) -> ValidationCheck:
    """Check retraction distance against extruder type.

    Direct drive: expected 0.5-3mm, WARN if > 3mm.
    Bowden: expected 3-8mm, WARN if < 3mm or > 8mm.
    """
    if analysis.retraction_distance_mm is None:
        return ValidationCheck(
            category=CheckCategory.RETRACTION,
            name="retraction_distance",
            severity=CheckSeverity.PASS,
            actual_value="not detected",
            expected_range="depends on extruder type",
            message="Retraction distance not detected in G-code",
            recommendation="",
        )

    distance = analysis.retraction_distance_mm

    if printer.extruder_type == ExtruderType.DIRECT_DRIVE:
        expected = "0.5-3mm (direct drive)"
        if distance > 3.0:
            return ValidationCheck(
                category=CheckCategory.RETRACTION,
                name="retraction_distance",
                severity=CheckSeverity.WARN,
                actual_value=f"{distance}mm",
                expected_range=expected,
                message=(
                    f"Retraction distance {distance}mm is too high for direct drive "
                    f"extruder (max 3mm recommended)"
                ),
                recommendation="Reduce retraction distance to 0.5-3mm for direct drive",
            )
    else:
        expected = "3-8mm (bowden)"
        if distance < 3.0:
            return ValidationCheck(
                category=CheckCategory.RETRACTION,
                name="retraction_distance",
                severity=CheckSeverity.WARN,
                actual_value=f"{distance}mm",
                expected_range=expected,
                message=(
                    f"Retraction distance {distance}mm is too low for bowden extruder "
                    f"(min 3mm recommended)"
                ),
                recommendation="Increase retraction distance to 3-8mm for bowden",
            )
        if distance > 8.0:
            return ValidationCheck(
                category=CheckCategory.RETRACTION,
                name="retraction_distance",
                severity=CheckSeverity.WARN,
                actual_value=f"{distance}mm",
                expected_range=expected,
                message=(
                    f"Retraction distance {distance}mm is too high for bowden extruder "
                    f"(max 8mm recommended)"
                ),
                recommendation="Reduce retraction distance to 3-8mm for bowden",
            )

    # Determine expected_range string for the PASS case
    if printer.extruder_type == ExtruderType.DIRECT_DRIVE:
        expected = "0.5-3mm (direct drive)"
    else:
        expected = "3-8mm (bowden)"

    return ValidationCheck(
        category=CheckCategory.RETRACTION,
        name="retraction_distance",
        severity=CheckSeverity.PASS,
        actual_value=f"{distance}mm",
        expected_range=expected,
        message=(
            f"Retraction distance {distance}mm is appropriate for {printer.extruder_type.value}"
        ),
        recommendation="",
    )


def check_first_layer(
    analysis: GcodeAnalysis,
    material: MaterialProfile,
) -> ValidationCheck:
    """Check first layer speed against best-practice range.

    First layer should typically be 15-30mm/s.
    WARN if above 30mm/s.
    """
    if analysis.first_layer_speed_mm_s is None:
        return ValidationCheck(
            category=CheckCategory.FIRST_LAYER,
            name="first_layer_speed",
            severity=CheckSeverity.PASS,
            actual_value="not detected",
            expected_range="15-30mm/s",
            message="First layer speed not detected in G-code",
            recommendation="",
        )

    speed = analysis.first_layer_speed_mm_s

    if speed > 30.0:
        return ValidationCheck(
            category=CheckCategory.FIRST_LAYER,
            name="first_layer_speed",
            severity=CheckSeverity.WARN,
            actual_value=f"{speed}mm/s",
            expected_range="15-30mm/s",
            message=(
                f"First layer speed {speed}mm/s is above the recommended "
                f"maximum of 30mm/s for good bed adhesion"
            ),
            recommendation="Reduce first layer speed to 15-30mm/s for better adhesion",
        )

    return ValidationCheck(
        category=CheckCategory.FIRST_LAYER,
        name="first_layer_speed",
        severity=CheckSeverity.PASS,
        actual_value=f"{speed}mm/s",
        expected_range="15-30mm/s",
        message=f"First layer speed {speed}mm/s is within recommended range",
        recommendation="",
    )


def check_build_volume(
    analysis: GcodeAnalysis,
    printer: PrinterProfile,
) -> ValidationCheck:
    """Check print dimensions against printer build volume.

    FAIL if any axis exceeds the printer's build volume (physical impossibility).
    PASS if fits or no dimensions available.
    """
    if analysis.print_dimensions is None:
        return ValidationCheck(
            category=CheckCategory.DIMENSIONS,
            name="build_volume",
            severity=CheckSeverity.PASS,
            actual_value="not detected",
            expected_range=(
                f"{printer.build_volume_x_mm}x"
                f"{printer.build_volume_y_mm}x"
                f"{printer.build_volume_z_mm}mm"
            ),
            message="Print dimensions not detected in G-code",
            recommendation="",
        )

    dims = analysis.print_dimensions
    actual = f"{dims.size_x:.1f}x{dims.size_y:.1f}x{dims.size_z:.1f}mm"
    expected = (
        f"{printer.build_volume_x_mm}x{printer.build_volume_y_mm}x{printer.build_volume_z_mm}mm"
    )

    exceeded = []
    if dims.size_x > printer.build_volume_x_mm:
        exceeded.append(f"X ({dims.size_x:.1f}mm > {printer.build_volume_x_mm}mm)")
    if dims.size_y > printer.build_volume_y_mm:
        exceeded.append(f"Y ({dims.size_y:.1f}mm > {printer.build_volume_y_mm}mm)")
    if dims.size_z > printer.build_volume_z_mm:
        exceeded.append(f"Z ({dims.size_z:.1f}mm > {printer.build_volume_z_mm}mm)")

    if exceeded:
        axes_str = ", ".join(exceeded)
        return ValidationCheck(
            category=CheckCategory.DIMENSIONS,
            name="build_volume",
            severity=CheckSeverity.FAIL,
            actual_value=actual,
            expected_range=expected,
            message=f"Print exceeds build volume on {axes_str}",
            recommendation=("Scale down the model or use a printer with a larger build volume"),
        )

    return ValidationCheck(
        category=CheckCategory.DIMENSIONS,
        name="build_volume",
        severity=CheckSeverity.PASS,
        actual_value=actual,
        expected_range=expected,
        message="Print fits within build volume",
        recommendation="",
    )


def check_print_time(
    analysis: GcodeAnalysis,
    max_hours: float = 72,
) -> ValidationCheck:
    """Check estimated print time against a threshold.

    WARN if print time exceeds max_hours (default 72 hours).
    """
    if analysis.estimated_time_s is None:
        return ValidationCheck(
            category=CheckCategory.TIME_ESTIMATE,
            name="print_time",
            severity=CheckSeverity.PASS,
            actual_value="not detected",
            expected_range=f"<{max_hours}h",
            message="Print time not detected in G-code",
            recommendation="",
        )

    time_s = analysis.estimated_time_s
    time_h = time_s / 3600.0
    max_seconds = max_hours * 3600.0

    if time_s > max_seconds:
        return ValidationCheck(
            category=CheckCategory.TIME_ESTIMATE,
            name="print_time",
            severity=CheckSeverity.WARN,
            actual_value=f"{time_h:.1f}h",
            expected_range=f"<{max_hours}h",
            message=(f"Estimated print time {time_h:.1f}h exceeds {max_hours}h threshold"),
            recommendation=(
                "Consider splitting the model into smaller parts or "
                "increasing layer height to reduce print time"
            ),
        )

    return ValidationCheck(
        category=CheckCategory.TIME_ESTIMATE,
        name="print_time",
        severity=CheckSeverity.PASS,
        actual_value=f"{time_h:.1f}h",
        expected_range=f"<{max_hours}h",
        message=f"Estimated print time {time_h:.1f}h is within threshold",
        recommendation="",
    )


def check_enclosure(
    analysis: GcodeAnalysis,
    material: MaterialProfile,
    printer: PrinterProfile,
) -> ValidationCheck:
    """Check enclosure and heated bed compatibility.

    FAIL if material requires enclosure but printer has none.
    FAIL if material requires heated bed but printer has none.
    These are physical requirements that will cause print failure.
    """
    issues = []

    if material.requires_enclosure and not printer.has_enclosure:
        issues.append("enclosure required but printer has none")

    if material.requires_heated_bed and not printer.has_heated_bed:
        issues.append("heated bed required but printer has none")

    if issues:
        issues_str = "; ".join(issues)
        recommendations = []
        if material.requires_enclosure and not printer.has_enclosure:
            recommendations.append(
                "use an enclosed printer or add an enclosure to prevent warping"
            )
        if material.requires_heated_bed and not printer.has_heated_bed:
            recommendations.append("use a printer with a heated bed for proper adhesion")

        return ValidationCheck(
            category=CheckCategory.COMPATIBILITY,
            name="enclosure_compatibility",
            severity=CheckSeverity.FAIL,
            actual_value=issues_str,
            expected_range=(
                f"enclosure={'required' if material.requires_enclosure else 'optional'}, "
                f"heated_bed={'required' if material.requires_heated_bed else 'optional'}"
            ),
            message=(f"{material.name} is incompatible with {printer.name}: {issues_str}"),
            recommendation="; ".join(recommendations),
        )

    enclosure_status = "enclosed" if printer.has_enclosure else "open"
    bed_status = "heated" if printer.has_heated_bed else "unheated"

    return ValidationCheck(
        category=CheckCategory.COMPATIBILITY,
        name="enclosure_compatibility",
        severity=CheckSeverity.PASS,
        actual_value=f"{enclosure_status}, {bed_status} bed",
        expected_range=(
            f"enclosure={'required' if material.requires_enclosure else 'optional'}, "
            f"heated_bed={'required' if material.requires_heated_bed else 'optional'}"
        ),
        message=f"Printer capabilities are compatible with {material.name}",
        recommendation="",
    )
