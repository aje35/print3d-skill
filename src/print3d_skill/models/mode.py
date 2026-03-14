"""Mode routing data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from print3d_skill.models.capability import ToolCapability


class WorkflowMode(str, Enum):
    """The five operating modes of the Print3D Skill."""

    CREATE = "create"
    FIX = "fix"
    MODIFY = "modify"
    DIAGNOSE = "diagnose"
    VALIDATE = "validate"


@dataclass
class ModeResponse:
    """Response from a workflow handler."""

    mode: str
    status: str  # "success", "error", "not_implemented"
    message: str
    data: dict[str, Any] | None = None


@dataclass
class SystemInfo:
    """Package capability summary."""

    package_version: str
    python_version: str
    capabilities: list[ToolCapability] = field(default_factory=list)
    core_available: bool = False
    extended_available: list[str] = field(default_factory=list)
    missing_extended: list[str] = field(default_factory=list)
