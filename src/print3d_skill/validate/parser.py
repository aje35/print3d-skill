"""Streaming G-code parser that builds a GcodeAnalysis report."""

from __future__ import annotations

import os
from pathlib import Path

from print3d_skill.exceptions import GcodeParseError
from print3d_skill.models.validate import (
    FanCommand,
    GcodeAnalysis,
    PrintDimensions,
    TemperatureCommand,
)
from print3d_skill.validate.extractors import (
    extract_fan,
    extract_layer_change,
    extract_metadata,
    extract_position,
    extract_retraction,
    extract_speed,
    extract_temperature,
)
from print3d_skill.validate.slicer_detect import detect_slicer


def parse_gcode_file(path: str) -> GcodeAnalysis:
    """Parse a G-code file line-by-line and return a structured analysis.

    Args:
        path: Path to the G-code file.

    Returns:
        GcodeAnalysis with all extracted parameters.

    Raises:
        GcodeParseError: If the file is empty or unreadable.
    """
    file_path = Path(path)
    file_size = file_path.stat().st_size

    if file_size == 0:
        raise GcodeParseError(f"G-code file is empty: {path}")

    # State tracking
    hotend_temps: list[TemperatureCommand] = []
    bed_temps: list[TemperatureCommand] = []
    chamber_temps: list[TemperatureCommand] = []
    fan_speeds: list[FanCommand] = []
    warnings: list[str] = []

    current_layer: int | None = None
    line_count = 0
    header_lines: list[str] = []

    # Extracted parameters
    print_speed_mm_s: float | None = None
    travel_speed_mm_s: float | None = None
    first_layer_speed_mm_s: float | None = None
    retraction_distance_mm: float | None = None
    retraction_speed_mm_s: float | None = None
    layer_height_mm: float | None = None
    first_layer_height_mm: float | None = None
    estimated_time_s: float | None = None
    estimated_filament_mm: float | None = None
    estimated_filament_g: float | None = None
    layer_count = 0

    # Bounding box tracking
    min_x = float("inf")
    max_x = float("-inf")
    min_y = float("inf")
    max_y = float("-inf")
    min_z = float("inf")
    max_z = float("-inf")
    has_moves = False

    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line_number, raw_line in enumerate(f, start=1):
                line = raw_line.strip()
                line_count = line_number

                # Collect header lines for slicer detection
                if line_number <= 100:
                    header_lines.append(line)

                if not line:
                    continue

                # Temperature extraction
                temp_result = extract_temperature(line)
                if temp_result is not None:
                    cmd = TemperatureCommand(
                        command=temp_result["command"],
                        target_temp_c=temp_result["target_temp_c"],
                        line_number=line_number,
                        layer=current_layer,
                        wait=temp_result["wait"],
                    )
                    if temp_result["type"] == "hotend":
                        hotend_temps.append(cmd)
                    elif temp_result["type"] == "bed":
                        bed_temps.append(cmd)
                    elif temp_result["type"] == "chamber":
                        chamber_temps.append(cmd)

                # Fan extraction
                fan_result = extract_fan(line)
                if fan_result is not None:
                    fan_speeds.append(
                        FanCommand(
                            command=fan_result["command"],
                            speed_percent=fan_result["speed_percent"],
                            line_number=line_number,
                            layer=current_layer,
                        )
                    )

                # Speed extraction
                speed_result = extract_speed(line)
                if speed_result is not None:
                    speed_mm_s = speed_result["feedrate_mm_min"] / 60.0
                    if speed_result["is_travel"]:
                        travel_speed_mm_s = speed_mm_s
                    else:
                        if current_layer is not None and current_layer == 0:
                            if first_layer_speed_mm_s is None:
                                first_layer_speed_mm_s = speed_mm_s
                        if print_speed_mm_s is None:
                            print_speed_mm_s = speed_mm_s

                # Retraction extraction
                retract_result = extract_retraction(line)
                if retract_result is not None:
                    if retract_result["type"] == "retract":
                        if retraction_distance_mm is None:
                            retraction_distance_mm = retract_result["distance_mm"]
                        if retract_result.get("speed_mm_min") and retraction_speed_mm_s is None:
                            retraction_speed_mm_s = retract_result["speed_mm_min"] / 60.0

                # Position extraction for bounding box
                pos_result = extract_position(line)
                if pos_result is not None:
                    if "x" in pos_result:
                        has_moves = True
                        min_x = min(min_x, pos_result["x"])
                        max_x = max(max_x, pos_result["x"])
                    if "y" in pos_result:
                        has_moves = True
                        min_y = min(min_y, pos_result["y"])
                        max_y = max(max_y, pos_result["y"])
                    if "z" in pos_result:
                        has_moves = True
                        min_z = min(min_z, pos_result["z"])
                        max_z = max(max_z, pos_result["z"])

                # Layer change detection
                layer_result = extract_layer_change(line)
                if layer_result is not None:
                    if layer_result.get("layer_number") is not None:
                        current_layer = layer_result["layer_number"]
                    elif current_layer is None:
                        current_layer = 0
                    else:
                        current_layer += 1
                    layer_count = max(layer_count, (current_layer or 0) + 1)

                # Metadata extraction
                slicer_name = None
                if line_number <= 100:
                    slicer_name = detect_slicer(header_lines)
                meta_result = extract_metadata(line, slicer=slicer_name)
                if meta_result is not None:
                    key = meta_result["key"]
                    value = meta_result["value"]
                    if key == "estimated_time_s" and estimated_time_s is None:
                        estimated_time_s = value
                    elif key == "filament_mm" and estimated_filament_mm is None:
                        estimated_filament_mm = value
                    elif key == "filament_g" and estimated_filament_g is None:
                        estimated_filament_g = value
                    elif key == "layer_height_mm" and layer_height_mm is None:
                        layer_height_mm = value
                    elif key == "first_layer_height_mm" and first_layer_height_mm is None:
                        first_layer_height_mm = value
                    elif key == "retraction_distance_mm" and retraction_distance_mm is None:
                        retraction_distance_mm = value
                    elif key == "retraction_speed_mm_s" and retraction_speed_mm_s is None:
                        retraction_speed_mm_s = value

    except OSError as exc:
        raise GcodeParseError(f"Cannot read G-code file: {path}: {exc}") from exc

    # Detect slicer from collected header lines
    slicer = detect_slicer(header_lines)

    # Build print dimensions if we have moves
    print_dimensions: PrintDimensions | None = None
    if has_moves and min_x != float("inf"):
        print_dimensions = PrintDimensions(
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y,
            min_z=min_z,
            max_z=max_z,
        )

    return GcodeAnalysis(
        file_path=str(os.path.abspath(path)),
        file_size_bytes=file_size,
        slicer=slicer,
        hotend_temps=hotend_temps,
        bed_temps=bed_temps,
        chamber_temps=chamber_temps,
        print_speed_mm_s=print_speed_mm_s,
        travel_speed_mm_s=travel_speed_mm_s,
        first_layer_speed_mm_s=first_layer_speed_mm_s,
        retraction_distance_mm=retraction_distance_mm,
        retraction_speed_mm_s=retraction_speed_mm_s,
        layer_height_mm=layer_height_mm,
        first_layer_height_mm=first_layer_height_mm,
        layer_count=layer_count if layer_count > 0 else None,
        estimated_time_s=estimated_time_s,
        estimated_filament_mm=estimated_filament_mm,
        estimated_filament_g=estimated_filament_g,
        fan_speeds=fan_speeds,
        print_dimensions=print_dimensions,
        line_count=line_count,
        warnings=warnings,
    )
