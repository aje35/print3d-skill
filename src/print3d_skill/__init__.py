"""print3d-skill: AI agent skill for full-stack 3D printing assistance.

Provides rendering, tool orchestration, domain knowledge, and
mode routing for LLM-powered 3D printing workflows.
"""

from __future__ import annotations

__version__ = "0.1.0"

from print3d_skill.analysis import analyze_mesh
from print3d_skill.export import export_mesh
from print3d_skill.knowledge import query_knowledge
from print3d_skill.rendering import render_preview
from print3d_skill.repair import repair_mesh
from print3d_skill.router import route
from print3d_skill.tools import (
    get_capability,
    list_capabilities,
    refresh_capabilities,
    system_info,
)

__all__ = [
    "analyze_mesh",
    "export_mesh",
    "get_capability",
    "list_capabilities",
    "query_knowledge",
    "refresh_capabilities",
    "render_preview",
    "repair_mesh",
    "route",
    "system_info",
]
