"""Manifold3d tool provider for boolean CSG operations."""

from __future__ import annotations

from print3d_skill.tools.base import ToolProvider


class ManifoldProvider(ToolProvider):
    """Provides boolean_operations capability via manifold3d."""

    name = "manifold3d"
    tier = "core"
    install_instructions = "pip install manifold3d"
    detection_method = "import"

    def detect(self) -> bool:
        try:
            import manifold3d
            self._version = getattr(manifold3d, "__version__", None)
            return True
        except ImportError:
            return False

    def get_capabilities(self) -> list[str]:
        return ["boolean_operations"]
