"""Parameter extraction functions for G-code line parsing.

Each function takes a single G-code line and returns a typed dict with
extracted parameters, or None if the line doesn't match. Uses only
Python stdlib (re module) with pre-compiled patterns.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Pre-compiled regex patterns
# ---------------------------------------------------------------------------

# Temperature commands
_RE_HOTEND_TEMP = re.compile(r"^(M10[49])\s.*?S(\d+\.?\d*)", re.IGNORECASE)
_RE_BED_TEMP = re.compile(r"^(M1[49]0)\s.*?S(\d+\.?\d*)", re.IGNORECASE)

# Speed / feedrate
_RE_SPEED = re.compile(r"^(G[01])\s(.*)$", re.IGNORECASE)
_RE_F_PARAM = re.compile(r"F(\d+\.?\d*)", re.IGNORECASE)
_RE_E_PARAM = re.compile(r"E(-?\d+\.?\d*)", re.IGNORECASE)

# Retraction — G1 with only E (and optional F), no X/Y/Z
_RE_RETRACT_G1 = re.compile(r"^G1\s+(?=.*E(-?\d+\.?\d*))(?!.*[XYZ])(.*)$", re.IGNORECASE)
_RE_FIRMWARE_RETRACT = re.compile(r"^G1[01]\b", re.IGNORECASE)

# Fan
_RE_FAN_ON = re.compile(r"^M106\s.*?S(\d+\.?\d*)", re.IGNORECASE)
_RE_FAN_ON_NO_S = re.compile(r"^M106\b", re.IGNORECASE)
_RE_FAN_OFF = re.compile(r"^M107\b", re.IGNORECASE)

# Position — X/Y/Z parameters in G0/G1 lines
_RE_MOVE = re.compile(r"^G[01]\s", re.IGNORECASE)
_RE_X = re.compile(r"X(-?\d+\.?\d*)", re.IGNORECASE)
_RE_Y = re.compile(r"Y(-?\d+\.?\d*)", re.IGNORECASE)
_RE_Z = re.compile(r"Z(-?\d+\.?\d*)", re.IGNORECASE)

# Layer change markers (slicer comments)
_RE_LAYER_PRUSA = re.compile(r"^;\s*LAYER_CHANGE\b")
_RE_LAYER_Z_PRUSA = re.compile(r"^;\s*Z:(\d+\.?\d*)")
_RE_LAYER_BAMBU = re.compile(r"^;\s*CHANGE_LAYER\b")
_RE_LAYER_CURA = re.compile(r"^;LAYER:(\d+)")

# Metadata — slicer comment fields
_RE_META_TIME_PRUSA = re.compile(
    r"^;\s*estimated printing time\s*(?:\(normal mode\))?\s*=\s*(.+)$", re.IGNORECASE
)
_RE_META_TIME_BAMBU = re.compile(r"^;\s*total estimated time:\s*(.+)$", re.IGNORECASE)
_RE_META_TIME_CURA = re.compile(r"^;TIME:(\d+\.?\d*)$")
_RE_META_FILAMENT_PRUSA = re.compile(r"^;\s*filament used \[mm\]\s*=\s*(\d+\.?\d*)", re.IGNORECASE)
_RE_META_FILAMENT_CURA = re.compile(r"^;Filament used:\s*(\d+\.?\d*)m?$", re.IGNORECASE)
_RE_META_LAYER_HEIGHT = re.compile(r"^;\s*layer_height\s*=\s*(\d+\.?\d*)", re.IGNORECASE)
_RE_META_LAYER_HEIGHT_CURA = re.compile(r"^;Layer height:\s*(\d+\.?\d*)", re.IGNORECASE)
_RE_META_RETRACT_LEN = re.compile(r"^;\s*retract(?:ion)?_length\s*=\s*(\d+\.?\d*)", re.IGNORECASE)
_RE_META_NOZZLE_TEMP = re.compile(r"^;\s*nozzle_temperature\s*=\s*(\d+\.?\d*)", re.IGNORECASE)
_RE_META_BED_TEMP = re.compile(r"^;\s*bed_temperature\s*=\s*(\d+\.?\d*)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Time string helpers
# ---------------------------------------------------------------------------


def _parse_time_string(time_str: str) -> float | None:
    """Convert human-readable time strings to seconds.

    Handles formats like ``1h 30m 15s``, ``1d 2h 30m``, ``45m 10s``, ``90``
    (bare number treated as seconds).
    """
    time_str = time_str.strip()

    # Bare number (already seconds)
    try:
        return float(time_str)
    except ValueError:
        pass

    total = 0.0
    found = False
    for match in re.finditer(r"(\d+\.?\d*)\s*([dhms])", time_str, re.IGNORECASE):
        found = True
        value = float(match.group(1))
        unit = match.group(2).lower()
        if unit == "d":
            total += value * 86400
        elif unit == "h":
            total += value * 3600
        elif unit == "m":
            total += value * 60
        else:
            total += value

    return total if found else None


# ---------------------------------------------------------------------------
# Extraction functions
# ---------------------------------------------------------------------------


def extract_temperature(line: str) -> dict | None:
    """Parse hotend/bed temperature commands (M104, M109, M140, M190).

    Returns:
        Dict with ``command``, ``target_temp_c``, ``type``, ``wait`` keys,
        or None if the line is not a temperature command.
    """
    line = line.strip()

    # Hotend: M104 (set) / M109 (wait)
    m = _RE_HOTEND_TEMP.match(line)
    if m:
        cmd = m.group(1).upper()
        return {
            "command": cmd,
            "target_temp_c": float(m.group(2)),
            "type": "hotend",
            "wait": cmd == "M109",
        }

    # Bed: M140 (set) / M190 (wait)
    m = _RE_BED_TEMP.match(line)
    if m:
        cmd = m.group(1).upper()
        return {
            "command": cmd,
            "target_temp_c": float(m.group(2)),
            "type": "bed",
            "wait": cmd == "M190",
        }

    return None


def extract_speed(line: str) -> dict | None:
    """Parse feedrate (F parameter) from G0/G1 move commands.

    Returns:
        Dict with ``feedrate_mm_min`` and ``is_travel`` keys,
        or None if the line is not a G0/G1 with an F parameter.
    """
    line = line.strip()

    m = _RE_SPEED.match(line)
    if not m:
        return None

    cmd = m.group(1).upper()
    params = m.group(2)

    f_match = _RE_F_PARAM.search(params)
    if not f_match:
        return None

    has_e = _RE_E_PARAM.search(params) is not None
    is_travel = cmd == "G0" or not has_e

    return {
        "feedrate_mm_min": float(f_match.group(1)),
        "is_travel": is_travel,
    }


def extract_retraction(line: str) -> dict | None:
    """Parse retraction and unretraction moves.

    Handles both G1-based retractions (negative E, no X/Y/Z) and firmware
    retract/unretract commands (G10/G11).

    Returns:
        Dict with ``type``, ``distance_mm``, ``speed_mm_min`` keys,
        or None if the line is not a retraction move.
    """
    line = line.strip()

    # Firmware retract (G10) / unretract (G11)
    upper = line.upper()
    if upper.startswith("G10") and (len(upper) == 3 or not upper[3].isdigit()):
        return {"type": "retract", "distance_mm": 0.0, "speed_mm_min": 0.0}
    if upper.startswith("G11") and (len(upper) == 3 or not upper[3].isdigit()):
        return {"type": "unretract", "distance_mm": 0.0, "speed_mm_min": 0.0}

    # G1 E-only moves (retract / unretract)
    m = _RE_RETRACT_G1.match(line)
    if not m:
        return None

    e_value = float(m.group(1))
    if e_value == 0.0:
        return None

    f_match = _RE_F_PARAM.search(line)
    speed = float(f_match.group(1)) if f_match else 0.0

    return {
        "type": "retract" if e_value < 0 else "unretract",
        "distance_mm": abs(e_value),
        "speed_mm_min": speed,
    }


def extract_fan(line: str) -> dict | None:
    """Parse fan control commands (M106 on, M107 off).

    Returns:
        Dict with ``command`` and ``speed_percent`` keys,
        or None if the line is not a fan command.
    """
    line = line.strip()

    # Fan off
    if _RE_FAN_OFF.match(line):
        return {"command": "M107", "speed_percent": 0.0}

    # Fan on with S parameter
    m = _RE_FAN_ON.match(line)
    if m:
        raw = float(m.group(1))
        percent = round(raw / 255.0 * 100.0, 1)
        return {"command": "M106", "speed_percent": percent}

    # Fan on without S parameter (defaults to full speed)
    if _RE_FAN_ON_NO_S.match(line):
        return {"command": "M106", "speed_percent": 100.0}

    return None


def extract_position(line: str) -> dict | None:
    """Parse X, Y, Z coordinates from G0/G1 move commands.

    Returns:
        Dict containing only the axes present in the line (e.g.
        ``{"x": 10.0, "y": 20.0}``), or None if no position parameters.
    """
    line = line.strip()

    if not _RE_MOVE.match(line):
        return None

    result: dict[str, float] = {}
    m = _RE_X.search(line)
    if m:
        result["x"] = float(m.group(1))
    m = _RE_Y.search(line)
    if m:
        result["y"] = float(m.group(1))
    m = _RE_Z.search(line)
    if m:
        result["z"] = float(m.group(1))

    return result if result else None


def extract_layer_change(line: str) -> dict | None:
    """Parse layer change markers from slicer comments.

    Supports PrusaSlicer (``LAYER_CHANGE``, ``Z:``), Bambu/Orca
    (``CHANGE_LAYER``), and Cura (``LAYER:N``).

    Returns:
        Dict with ``layer_number`` and ``z_height`` keys (either may be None),
        or None if the line is not a layer change marker.
    """
    line = line.strip()

    # PrusaSlicer: "; LAYER_CHANGE"
    if _RE_LAYER_PRUSA.match(line):
        return {"layer_number": None, "z_height": None}

    # PrusaSlicer: "; Z:0.300"
    m = _RE_LAYER_Z_PRUSA.match(line)
    if m:
        return {"layer_number": None, "z_height": float(m.group(1))}

    # Bambu/Orca: "; CHANGE_LAYER"
    if _RE_LAYER_BAMBU.match(line):
        return {"layer_number": None, "z_height": None}

    # Cura: ";LAYER:5"
    m = _RE_LAYER_CURA.match(line)
    if m:
        return {"layer_number": int(m.group(1)), "z_height": None}

    return None


def extract_metadata(line: str, slicer: str | None = None) -> dict | None:
    """Parse slicer-specific metadata from comment lines.

    Extracts print time, filament usage, layer height, retraction distance,
    nozzle temperature, and bed temperature from slicer header/footer comments.

    Args:
        line: A single G-code line.
        slicer: Optional slicer hint (unused currently; patterns are tried
            in order for all slicers).

    Returns:
        Dict with ``key`` and ``value`` keys, or None if no metadata found.
    """
    line = line.strip()

    # --- Estimated print time ---

    m = _RE_META_TIME_PRUSA.match(line)
    if m:
        seconds = _parse_time_string(m.group(1))
        if seconds is not None:
            return {"key": "estimated_time_s", "value": seconds}

    m = _RE_META_TIME_BAMBU.match(line)
    if m:
        seconds = _parse_time_string(m.group(1))
        if seconds is not None:
            return {"key": "estimated_time_s", "value": seconds}

    m = _RE_META_TIME_CURA.match(line)
    if m:
        return {"key": "estimated_time_s", "value": float(m.group(1))}

    # --- Filament usage ---

    m = _RE_META_FILAMENT_PRUSA.match(line)
    if m:
        return {"key": "filament_mm", "value": float(m.group(1))}

    m = _RE_META_FILAMENT_CURA.match(line)
    if m:
        # Cura reports in meters; convert to mm
        return {"key": "filament_mm", "value": float(m.group(1)) * 1000.0}

    # --- Layer height ---

    m = _RE_META_LAYER_HEIGHT.match(line)
    if m:
        return {"key": "layer_height_mm", "value": float(m.group(1))}

    m = _RE_META_LAYER_HEIGHT_CURA.match(line)
    if m:
        return {"key": "layer_height_mm", "value": float(m.group(1))}

    # --- Retraction distance ---

    m = _RE_META_RETRACT_LEN.match(line)
    if m:
        return {"key": "retraction_distance_mm", "value": float(m.group(1))}

    # --- Nozzle temperature ---

    m = _RE_META_NOZZLE_TEMP.match(line)
    if m:
        return {"key": "nozzle_temperature_c", "value": float(m.group(1))}

    # --- Bed temperature ---

    m = _RE_META_BED_TEMP.match(line)
    if m:
        return {"key": "bed_temperature_c", "value": float(m.group(1))}

    return None
