"""Printer control tool provider (extended tier).

Detects whether a printer config file exists and registers
the printer_control capability.
"""

from __future__ import annotations

import sys
from pathlib import Path

from print3d_skill.tools.base import ToolProvider


class PrinterProvider(ToolProvider):
    """Provides printer_control capability when a config file exists.

    Detection checks for the platform-appropriate config file at:
    - macOS: ~/Library/Application Support/print3d-skill/printers.yaml
    - Linux: ~/.config/print3d-skill/printers.yaml
    """

    name = "printer"
    tier = "extended"
    install_instructions = (
        "Create a printer config file at "
        "~/.config/print3d-skill/printers.yaml (Linux) or "
        "~/Library/Application Support/print3d-skill/printers.yaml (macOS). "
        "See docs for format."
    )
    detection_method = "config file"

    def detect(self) -> bool:
        """Check if a printer config file exists."""
        path = self._config_path()
        return path.exists()

    def get_capabilities(self) -> list[str]:
        return ["printer_control"]

    @staticmethod
    def _config_path() -> Path:
        """Return the platform-appropriate config file path."""
        if sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path.home() / ".config"
        return base / "print3d-skill" / "printers.yaml"
