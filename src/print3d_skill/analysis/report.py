"""Report builder with health score calculation and classification logic."""

from __future__ import annotations

from print3d_skill.models.analysis import (
    DefectSeverity,
    MeshAnalysisReport,
    MeshDefect,
    MeshHealthClassification,
    ShellAnalysis,
)
from print3d_skill.models.mesh import BoundingBox


def compute_health_score(defects: list[MeshDefect], face_count: int) -> float:
    """Compute mesh health score from 0.0 to 1.0.

    Scoring per research.md R7:
    - Start at 1.0
    - Critical defects: -0.1 per element, capped at -0.6
    - Warning defects: -0.05 per element, capped at -0.3
    - Info defects: -0.01 per element, capped at -0.1
    - Floor at 0.0
    """
    if not defects:
        return 1.0

    score = 1.0

    # Group by severity
    critical_count = sum(
        d.count for d in defects if d.severity == DefectSeverity.critical
    )
    warning_count = sum(
        d.count for d in defects if d.severity == DefectSeverity.warning
    )
    info_count = sum(
        d.count for d in defects if d.severity == DefectSeverity.info
    )

    # Apply weighted penalties with caps
    # Normalize by face count to make scoring relative to mesh size
    if face_count > 0:
        critical_ratio = critical_count / face_count
        warning_ratio = warning_count / face_count
        info_ratio = info_count / face_count
    else:
        critical_ratio = critical_count
        warning_ratio = warning_count
        info_ratio = info_count

    critical_penalty = min(critical_ratio * 0.1 * face_count, 0.6)
    warning_penalty = min(warning_ratio * 0.05 * face_count, 0.3)
    info_penalty = min(info_ratio * 0.01 * face_count, 0.1)

    # Simpler approach: penalty proportional to defect count
    critical_penalty = min(critical_count * 0.1, 0.6)
    warning_penalty = min(warning_count * 0.05, 0.3)
    info_penalty = min(info_count * 0.01, 0.1)

    score -= critical_penalty + warning_penalty + info_penalty
    return max(score, 0.0)


def classify_health(score: float) -> MeshHealthClassification:
    """Classify mesh health based on score thresholds.

    >= 0.8: print_ready
    0.3 - 0.8: repairable
    < 0.3: severely_damaged
    """
    if score >= 0.8:
        return MeshHealthClassification.print_ready
    if score >= 0.3:
        return MeshHealthClassification.repairable
    return MeshHealthClassification.severely_damaged


def build_report(
    mesh_path: str,
    fmt: str,
    detected_units: str,
    vertex_count: int,
    face_count: int,
    bounding_box: BoundingBox,
    shell_count: int,
    shells: list[ShellAnalysis],
    defects: list[MeshDefect],
    is_triangulated: bool,
) -> MeshAnalysisReport:
    """Build a complete MeshAnalysisReport from analysis results."""
    health_score = compute_health_score(defects, face_count)
    classification = classify_health(health_score)

    return MeshAnalysisReport(
        mesh_path=mesh_path,
        format=fmt,
        detected_units=detected_units,
        vertex_count=vertex_count,
        face_count=face_count,
        bounding_box=bounding_box,
        shell_count=shell_count,
        shells=shells,
        defects=defects,
        health_score=health_score,
        classification=classification,
        is_triangulated=is_triangulated,
    )
