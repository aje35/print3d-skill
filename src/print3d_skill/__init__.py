"""print3d-skill: AI agent skill for full-stack 3D printing assistance.

Provides rendering, tool orchestration, domain knowledge, and
mode routing for LLM-powered 3D printing workflows.
"""

from __future__ import annotations

__version__ = "0.1.0"

from print3d_skill.analysis import analyze_mesh
from print3d_skill.create import create_design, validate_printability
from print3d_skill.diagnosis import diagnose_print
from print3d_skill.export import export_mesh
from print3d_skill.knowledge import query_knowledge
from print3d_skill.modify import modify_mesh
from print3d_skill.printing import list_printers, submit_print
from print3d_skill.rendering import render_preview
from print3d_skill.repair import repair_mesh
from print3d_skill.router import route
from print3d_skill.slicing import slice_model
from print3d_skill.tools import (
    get_capability,
    list_capabilities,
    refresh_capabilities,
    system_info,
)
from print3d_skill.validate import parse_gcode, validate_gcode

__all__ = [
    "analyze_mesh",
    "create_design",
    "diagnose_print",
    "export_mesh",
    "get_capability",
    "list_capabilities",
    "list_printers",
    "modify_mesh",
    "parse_gcode",
    "query_knowledge",
    "refresh_capabilities",
    "render_preview",
    "repair_mesh",
    "route",
    "slice_model",
    "submit_print",
    "system_info",
    "validate_gcode",
    "validate_printability",
]
