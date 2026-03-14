"""Load material and printer profiles from the knowledge system for validation."""

from __future__ import annotations

from print3d_skill.knowledge import query_knowledge
from print3d_skill.models.validate import ExtruderType, MaterialProfile, PrinterProfile


def _parse_retraction(value: object) -> float:
    """Parse a retraction value that may be a range string like '0.5-2.0' or a number."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and "-" in value:
        parts = value.split("-")
        try:
            return float(parts[-1])
        except ValueError:
            return 0.0
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def load_material_profile(name: str) -> MaterialProfile | None:
    """Load a material profile by name from the knowledge base.

    Returns None if no matching material_properties file is found.
    """
    results = query_knowledge(mode="validate", material=name)

    material_file = None
    for kf in results:
        if kf.metadata.type == "material_properties":
            material_file = kf
            break

    if material_file is None:
        return None

    props = material_file.data.get("properties", {})
    if not props:
        return None

    return MaterialProfile(
        name=name,
        hotend_temp_min_c=float(props.get("hotend_temp_min_c", 0)),
        hotend_temp_max_c=float(props.get("hotend_temp_max_c", 0)),
        bed_temp_min_c=float(props.get("bed_temp_min_c", 0)),
        bed_temp_max_c=float(props.get("bed_temp_max_c", 0)),
        speed_min_mm_s=float(props.get("print_speed_min_mm_s", 0)),
        speed_max_mm_s=float(props.get("print_speed_max_mm_s", 0)),
        retraction_direct_drive_mm=_parse_retraction(props.get("retraction_direct_drive_mm", 0)),
        retraction_bowden_mm=_parse_retraction(props.get("retraction_bowden_mm", 0)),
        retraction_speed_mm_s=float(props.get("retraction_speed_mm_s", 0)),
        requires_enclosure=bool(props.get("requires_enclosure", False)),
        requires_heated_bed=bool(props.get("requires_heated_bed", False)),
        fan_speed_percent=float(props.get("fan_speed_percent", 0)),
        notes=list(props.get("notes", [])),
    )


def load_printer_profile(name: str) -> PrinterProfile | None:
    """Load a printer profile by name from the knowledge base.

    Performs case-insensitive matching against profile keys.
    Returns None if no matching profile is found.
    """
    results = query_knowledge(mode="validate")

    profiles: dict[str, object] = {}
    for kf in results:
        if kf.metadata.type == "printer_capabilities":
            profiles = kf.data.get("profiles", {})
            break

    if not profiles:
        return None

    # Case-insensitive lookup
    name_lower = name.lower()
    matched_data = None
    for key, value in profiles.items():
        if key.lower() == name_lower:
            matched_data = value
            break

    if matched_data is None or not isinstance(matched_data, dict):
        return None

    # Convert extruder_type string to ExtruderType enum
    extruder_str = matched_data.get("extruder_type", "direct_drive")
    try:
        extruder_type = ExtruderType(extruder_str)
    except ValueError:
        extruder_type = ExtruderType.DIRECT_DRIVE

    return PrinterProfile(
        name=name,
        build_volume_x_mm=float(matched_data.get("build_volume_x_mm", 0)),
        build_volume_y_mm=float(matched_data.get("build_volume_y_mm", 0)),
        build_volume_z_mm=float(matched_data.get("build_volume_z_mm", 0)),
        max_hotend_temp_c=float(matched_data.get("max_hotend_temp_c", 0)),
        max_bed_temp_c=float(matched_data.get("max_bed_temp_c", 0)),
        extruder_type=extruder_type,
        has_heated_bed=bool(matched_data.get("has_heated_bed", True)),
        has_enclosure=bool(matched_data.get("has_enclosure", False)),
        notes=list(matched_data.get("notes", [])),
    )
