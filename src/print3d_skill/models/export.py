"""Mesh export data models."""

from __future__ import annotations

from dataclasses import dataclass, field

from print3d_skill.models.analysis import MeshAnalysisReport
from print3d_skill.models.repair import RepairSummary


@dataclass
class ExportResult:
    paths: dict[str, str] = field(default_factory=dict)
    repair_summary: RepairSummary | None = None
    analysis_report: MeshAnalysisReport | None = None
