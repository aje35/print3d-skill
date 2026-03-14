"""Mesh analysis data models for defect detection and health reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from print3d_skill.models.mesh import BoundingBox


class DefectSeverity(str, Enum):
    """Severity level of a mesh defect."""

    critical = "critical"
    warning = "warning"
    info = "info"


class DefectType(str, Enum):
    """Types of mesh defects that can be detected during analysis."""

    # Critical defects
    non_manifold_edges = "non_manifold_edges"
    non_manifold_vertices = "non_manifold_vertices"
    boundary_edges = "boundary_edges"
    non_watertight = "non_watertight"

    # Warning defects
    inconsistent_normals = "inconsistent_normals"
    self_intersecting = "self_intersecting"

    # Info defects
    degenerate_faces = "degenerate_faces"
    duplicate_vertices = "duplicate_vertices"
    duplicate_faces = "duplicate_faces"
    excessive_poly_count = "excessive_poly_count"

    @property
    def severity(self) -> DefectSeverity:
        """Return the severity level associated with this defect type."""
        severity_map: dict[DefectType, DefectSeverity] = {
            DefectType.non_manifold_edges: DefectSeverity.critical,
            DefectType.non_manifold_vertices: DefectSeverity.critical,
            DefectType.boundary_edges: DefectSeverity.critical,
            DefectType.non_watertight: DefectSeverity.critical,
            DefectType.inconsistent_normals: DefectSeverity.warning,
            DefectType.self_intersecting: DefectSeverity.warning,
            DefectType.degenerate_faces: DefectSeverity.info,
            DefectType.duplicate_vertices: DefectSeverity.info,
            DefectType.duplicate_faces: DefectSeverity.info,
            DefectType.excessive_poly_count: DefectSeverity.info,
        }
        return severity_map[self]


class MeshHealthClassification(str, Enum):
    """Overall health classification of a mesh."""

    print_ready = "print_ready"
    repairable = "repairable"
    severely_damaged = "severely_damaged"


@dataclass
class MeshDefect:
    """A single detected defect in a mesh."""

    defect_type: DefectType
    severity: DefectSeverity
    count: int
    affected_indices: list[int]
    description: str


@dataclass
class ShellAnalysis:
    """Analysis results for an individual shell within a mesh."""

    shell_index: int
    vertex_count: int
    face_count: int
    bounding_box: BoundingBox
    is_watertight: bool
    defects: list[MeshDefect] = field(default_factory=list)


@dataclass
class MeshAnalysisReport:
    """Complete analysis report for a 3D mesh file."""

    mesh_path: str
    format: str
    detected_units: str
    vertex_count: int
    face_count: int
    bounding_box: BoundingBox
    shell_count: int
    shells: list[ShellAnalysis]
    defects: list[MeshDefect]
    health_score: float
    classification: MeshHealthClassification
    is_triangulated: bool
