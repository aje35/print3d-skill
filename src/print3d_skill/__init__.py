"""print3d-skill: AI agent skill for full-stack 3D printing assistance.

Provides rendering, tool orchestration, domain knowledge, and
mode routing for LLM-powered 3D printing workflows.
"""

from __future__ import annotations

__version__ = "0.1.0"

from print3d_skill.knowledge import query_knowledge
from print3d_skill.rendering import render_preview
from print3d_skill.router import route
from print3d_skill.tools import (
    get_capability,
    list_capabilities,
    refresh_capabilities,
    system_info,
)

__all__ = [
    "render_preview",
    "get_capability",
    "list_capabilities",
    "refresh_capabilities",
    "query_knowledge",
    "route",
    "system_info",
]
