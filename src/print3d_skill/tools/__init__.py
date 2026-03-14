"""Tool orchestration layer with capability-based discovery.

Public API: get_capability(), list_capabilities(), refresh_capabilities(),
            system_info()
"""

from __future__ import annotations

import platform

from print3d_skill.exceptions import CapabilityUnavailable as CapabilityUnavailable
from print3d_skill.models.capability import ToolCapability
from print3d_skill.models.mode import SystemInfo
from print3d_skill.tools.base import ToolProvider
from print3d_skill.tools.manifold_tools import ManifoldProvider
from print3d_skill.tools.openscad import OpenSCADProvider
from print3d_skill.tools.printer_tools import PrinterProvider
from print3d_skill.tools.registry import ToolRegistry
from print3d_skill.tools.slicer_tools import SlicerProvider
from print3d_skill.tools.trimesh_tools import TrimeshProvider

# Default registry with all known providers
_registry = ToolRegistry()
_registry.register(TrimeshProvider())
_registry.register(ManifoldProvider())
_registry.register(OpenSCADProvider())
_registry.register(SlicerProvider())
_registry.register(PrinterProvider())


def get_capability(name: str) -> ToolProvider:
    """Get a tool provider for the named capability.

    Raises:
        CapabilityUnavailable: no provider available for this
            capability. Exception includes: capability name,
            tool that would provide it, install instructions.
    """
    return _registry.get(name)


def list_capabilities() -> list[ToolCapability]:
    """List all known capabilities and their availability status."""
    return _registry.list_all()


def refresh_capabilities() -> list[ToolCapability]:
    """Re-detect all tool availability and return updated list."""
    return _registry.refresh()


def system_info() -> SystemInfo:
    """Report package version, capabilities, and missing deps."""
    import print3d_skill

    caps = list_capabilities()
    core_caps = [c for c in caps if c.tier == "core"]
    extended_caps = [c for c in caps if c.tier == "extended"]

    return SystemInfo(
        package_version=print3d_skill.__version__,
        python_version=platform.python_version(),
        capabilities=caps,
        core_available=all(c.is_available for c in core_caps),
        extended_available=[c.name for c in extended_caps if c.is_available],
        missing_extended=[c.name for c in extended_caps if not c.is_available],
    )
