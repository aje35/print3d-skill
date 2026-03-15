"""Diagnosis data models.

Dataclasses for print defect identification, root cause analysis,
and fix recommendation generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PrintDefectCategory(str, Enum):
    """The 12 recognized print defect categories."""

    stringing = "stringing"
    layer_shift = "layer_shift"
    warping = "warping"
    under_extrusion = "under_extrusion"
    over_extrusion = "over_extrusion"
    bed_adhesion_failure = "bed_adhesion_failure"
    elephant_foot = "elephant_foot"
    poor_bridging = "poor_bridging"
    support_scarring = "support_scarring"
    layer_separation = "layer_separation"
    zits_blobs = "zits_blobs"
    ghosting = "ghosting"


class PrintDefectSeverity(str, Enum):
    """Three-level severity assigned per defect category."""

    cosmetic = "cosmetic"
    functional = "functional"
    print_stopping = "print_stopping"


@dataclass
class PrintDefect:
    """A print quality problem identified by the agent from photo analysis."""

    category: PrintDefectCategory
    description: str
    confidence: str  # "high", "medium", "low"
    severity: PrintDefectSeverity | None = None
    spatial_distribution: str = "global"  # "localized", "regional", "global"


@dataclass
class DiagnosticContext:
    """User's setup information for cross-referencing during root cause analysis."""

    printer_model: str | None = None
    printer_family: str | None = None  # "bambu", "prusa", "creality"
    extruder_type: str | None = None  # "direct_drive", "bowden"
    material: str | None = None  # "PLA", "PETG", "ABS", "TPU", "ASA"
    slicer_settings: dict[str, Any] | None = None
    geometry_info: dict[str, Any] | None = None


@dataclass
class RootCause:
    """A determined reason for a defect, derived from walking a decision tree."""

    description: str
    likelihood: str  # "high", "medium", "low"
    contributing_factors: list[str]
    defect_category: PrintDefectCategory


@dataclass
class Recommendation:
    """A specific fix for a root cause."""

    setting: str
    current_issue: str
    suggested_value: str
    impact: str  # "high", "medium", "low"
    difficulty: str  # "easy", "moderate", "hard"
    category: str  # "controllable", "environmental"
    explanation: str


@dataclass
class DiagnosisResult:
    """Complete output of the diagnosis pipeline."""

    defects: list[PrintDefect]
    context: DiagnosticContext
    root_causes: list[RootCause] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    context_quality: str = "minimal"  # "full", "partial", "minimal"
