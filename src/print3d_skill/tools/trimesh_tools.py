"""Trimesh tool provider for mesh loading and analysis."""

from __future__ import annotations

from print3d_skill.tools.base import ToolProvider


class TrimeshProvider(ToolProvider):
    """Provides mesh_loading and mesh_analysis capabilities via trimesh."""

    name = "trimesh"
    tier = "core"
    install_instructions = "pip install trimesh"
    detection_method = "import"

    def detect(self) -> bool:
        try:
            import trimesh

            self._version = trimesh.__version__
            return True
        except ImportError:
            return False

    def get_capabilities(self) -> list[str]:
        return ["mesh_loading", "mesh_analysis"]
