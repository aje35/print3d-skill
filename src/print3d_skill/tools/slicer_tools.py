"""Slicer tool provider for G-code slicing via CLI."""

from __future__ import annotations

import shutil

from print3d_skill.tools.base import ToolProvider


class SlicerProvider(ToolProvider):
    """Provides gcode_slicing via PrusaSlicer or OrcaSlicer CLI."""

    name = "slicer"
    tier = "extended"
    install_instructions = (
        "Install PrusaSlicer (https://github.com/prusa3d/PrusaSlicer) "
        "or OrcaSlicer (https://github.com/SoftFever/OrcaSlicer) "
        "and ensure the CLI is on PATH"
    )
    detection_method = "shutil.which"

    def detect(self) -> bool:
        for exe in ("prusa-slicer", "PrusaSlicer", "orca-slicer", "OrcaSlicer"):
            if shutil.which(exe) is not None:
                self._version = exe
                return True
        return False

    def get_capabilities(self) -> list[str]:
        return ["gcode_slicing"]
