"""Mesh repair data models for repair strategies and pipeline results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from print3d_skill.models.analysis import DefectType, MeshAnalysisReport, MeshDefect


class RepairStrategy(str, Enum):
    merge_vertices = "merge_vertices"
    remove_degenerates = "remove_degenerates"
    fill_holes = "fill_holes"
    fix_normals = "fix_normals"
    remove_duplicates = "remove_duplicates"
    decimate = "decimate"


@dataclass
class RepairResult:
    strategy: RepairStrategy
    defect_type: DefectType
    success: bool
    elements_affected: int
    description: str
    before_preview_path: str | None = None
    after_preview_path: str | None = None


@dataclass
class RepairConfig:
    vertex_merge_tolerance: float = 1e-8
    degenerate_area_threshold: float = 1e-10
    max_poly_count: int = 1_000_000
    decimation_target: int | None = None
    export_formats: list[str] = field(default_factory=lambda: ["stl", "3mf"])
    output_dir: str | None = None
    render_previews: bool = True


@dataclass
class RepairSummary:
    mesh_path: str
    initial_analysis: MeshAnalysisReport
    final_analysis: MeshAnalysisReport
    repairs: list[RepairResult]
    total_defects_found: int
    total_defects_fixed: int
    remaining_defects: list[MeshDefect]
    export_paths: dict[str, str] = field(default_factory=dict)
    classification_changed: bool = False
    severely_damaged_warning: str | None = None
