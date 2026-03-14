"""OpenSCAD tool provider for CAD compilation and rendering."""

from __future__ import annotations

import shutil
import subprocess

from print3d_skill.tools.base import ToolProvider


class OpenSCADProvider(ToolProvider):
    """Provides cad_compilation and cad_rendering via OpenSCAD CLI."""

    name = "openscad"
    tier = "extended"
    install_instructions = (
        "Install OpenSCAD: brew install openscad (macOS), "
        "apt install openscad (Ubuntu), "
        "choco install openscad (Windows)"
    )
    detection_method = "shutil.which"

    def detect(self) -> bool:
        path = shutil.which("openscad")
        if path is None:
            return False

        try:
            result = subprocess.run(
                ["openscad", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # OpenSCAD prints version to stderr
            version_text = result.stderr.strip() or result.stdout.strip()
            if version_text:
                self._version = version_text.split()[-1] if version_text.split() else version_text
        except (subprocess.TimeoutExpired, OSError):
            pass

        return True

    def get_capabilities(self) -> list[str]:
        return ["cad_compilation", "cad_rendering"]
