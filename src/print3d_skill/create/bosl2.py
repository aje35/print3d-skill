"""BOSL2 library detection and availability."""

from __future__ import annotations

import shutil
import subprocess

_bosl2_available: bool | None = None


def detect_bosl2() -> bool:
    """Check if the BOSL2 library is installed and available to OpenSCAD.

    Runs a test compile of ``include <BOSL2/std.scad>`` via the OpenSCAD CLI.
    The result is cached after the first call so subsequent checks are free.

    Returns:
        True if BOSL2 is installed and OpenSCAD can include it.
    """
    global _bosl2_available  # noqa: PLW0603
    if _bosl2_available is not None:
        return _bosl2_available

    openscad = shutil.which("openscad")
    if openscad is None:
        _bosl2_available = False
        return False

    try:
        result = subprocess.run(
            [openscad, "-o", "/dev/null", "-e", "include <BOSL2/std.scad>;"],
            capture_output=True,
            timeout=30,
        )
        _bosl2_available = result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        _bosl2_available = False

    return _bosl2_available


def _reset_cache() -> None:
    """Reset the cached BOSL2 detection result (for testing)."""
    global _bosl2_available  # noqa: PLW0603
    _bosl2_available = None
