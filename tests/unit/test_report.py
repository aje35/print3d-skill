"""Unit tests for the report builder, health score, and classification (US6).

Covers compute_health_score(), classify_health(), and build_report().
"""

from __future__ import annotations

import pytest

from print3d_skill.analysis.report import (
    build_report,
    classify_health,
    compute_health_score,
)
from print3d_skill.models.analysis import (
    DefectSeverity,
    DefectType,
    MeshAnalysisReport,
    MeshDefect,
    MeshHealthClassification,
)
from print3d_skill.models.mesh import BoundingBox


# ---------------------------------------------------------------------------
# Helpers — factory for MeshDefect instances
# ---------------------------------------------------------------------------

def _defect(
    defect_type: DefectType,
    count: int = 1,
) -> MeshDefect:
    return MeshDefect(
        defect_type=defect_type,
        severity=defect_type.severity,
        count=count,
        affected_indices=[],
        description=f"test defect: {defect_type.value}",
    )


# ---------------------------------------------------------------------------
# compute_health_score
# ---------------------------------------------------------------------------

class TestComputeHealthScore:
    def test_no_defects_returns_1(self):
        score = compute_health_score([], face_count=100)
        assert score == 1.0

    def test_critical_defects_reduce_score(self):
        defects = [_defect(DefectType.boundary_edges, count=3)]
        score = compute_health_score(defects, face_count=100)
        # 3 critical elements * 0.1 = 0.3 penalty → score = 0.7
        assert score < 1.0
        assert score == pytest.approx(0.7)

    def test_warning_defects_reduce_score(self):
        defects = [_defect(DefectType.inconsistent_normals, count=4)]
        score = compute_health_score(defects, face_count=100)
        # 4 warning elements * 0.05 = 0.2 penalty → score = 0.8
        assert score < 1.0
        assert score == pytest.approx(0.8)

    def test_info_defects_reduce_score(self):
        defects = [_defect(DefectType.degenerate_faces, count=5)]
        score = compute_health_score(defects, face_count=100)
        # 5 info elements * 0.01 = 0.05 penalty → score = 0.95
        assert score < 1.0
        assert score == pytest.approx(0.95)

    def test_all_severity_types_combined(self):
        defects = [
            _defect(DefectType.non_watertight, count=1),        # critical: 0.1
            _defect(DefectType.inconsistent_normals, count=2),   # warning:  0.1
            _defect(DefectType.duplicate_vertices, count=3),     # info:     0.03
        ]
        score = compute_health_score(defects, face_count=100)
        expected = 1.0 - 0.1 - 0.1 - 0.03
        assert score == pytest.approx(expected)

    def test_critical_penalty_capped_at_0_6(self):
        defects = [_defect(DefectType.boundary_edges, count=100)]
        score = compute_health_score(defects, face_count=200)
        # 100 * 0.1 = 10, capped at 0.6 → score = 0.4
        assert score == pytest.approx(0.4)

    def test_warning_penalty_capped_at_0_3(self):
        defects = [_defect(DefectType.self_intersecting, count=100)]
        score = compute_health_score(defects, face_count=200)
        # 100 * 0.05 = 5, capped at 0.3 → score = 0.7
        assert score == pytest.approx(0.7)

    def test_info_penalty_capped_at_0_1(self):
        defects = [_defect(DefectType.degenerate_faces, count=100)]
        score = compute_health_score(defects, face_count=200)
        # 100 * 0.01 = 1, capped at 0.1 → score = 0.9
        assert score == pytest.approx(0.9)

    def test_floor_at_zero(self):
        defects = [
            _defect(DefectType.boundary_edges, count=100),       # -0.6
            _defect(DefectType.self_intersecting, count=100),    # -0.3
            _defect(DefectType.degenerate_faces, count=100),     # -0.1
        ]
        score = compute_health_score(defects, face_count=200)
        assert score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# classify_health
# ---------------------------------------------------------------------------

class TestClassifyHealth:
    def test_high_score_is_print_ready(self):
        assert classify_health(0.9) == MeshHealthClassification.print_ready

    def test_threshold_0_8_is_print_ready(self):
        assert classify_health(0.8) == MeshHealthClassification.print_ready

    def test_medium_score_is_repairable(self):
        assert classify_health(0.5) == MeshHealthClassification.repairable

    def test_threshold_0_3_is_repairable(self):
        assert classify_health(0.3) == MeshHealthClassification.repairable

    def test_low_score_is_severely_damaged(self):
        assert classify_health(0.1) == MeshHealthClassification.severely_damaged

    def test_zero_score_is_severely_damaged(self):
        assert classify_health(0.0) == MeshHealthClassification.severely_damaged

    def test_perfect_score_is_print_ready(self):
        assert classify_health(1.0) == MeshHealthClassification.print_ready

    def test_just_below_0_8_is_repairable(self):
        assert classify_health(0.79) == MeshHealthClassification.repairable

    def test_just_below_0_3_is_severely_damaged(self):
        assert classify_health(0.29) == MeshHealthClassification.severely_damaged


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------

class TestBuildReport:
    @pytest.fixture()
    def sample_bbox(self) -> BoundingBox:
        return BoundingBox(
            min_point=(-10.0, -10.0, -10.0),
            max_point=(10.0, 10.0, 10.0),
        )

    def test_produces_valid_report_no_defects(self, sample_bbox: BoundingBox):
        report = build_report(
            mesh_path="/tmp/test.stl",
            fmt="stl",
            detected_units="mm",
            vertex_count=8,
            face_count=12,
            bounding_box=sample_bbox,
            shell_count=1,
            shells=[],
            defects=[],
            is_triangulated=True,
        )
        assert isinstance(report, MeshAnalysisReport)
        assert report.mesh_path == "/tmp/test.stl"
        assert report.format == "stl"
        assert report.detected_units == "mm"
        assert report.vertex_count == 8
        assert report.face_count == 12
        assert report.bounding_box is sample_bbox
        assert report.shell_count == 1
        assert report.shells == []
        assert report.defects == []
        assert report.health_score == 1.0
        assert report.classification == MeshHealthClassification.print_ready
        assert report.is_triangulated is True

    def test_report_with_defects_has_reduced_score(self, sample_bbox: BoundingBox):
        defects = [_defect(DefectType.boundary_edges, count=3)]
        report = build_report(
            mesh_path="/tmp/holed.stl",
            fmt="stl",
            detected_units="mm",
            vertex_count=100,
            face_count=200,
            bounding_box=sample_bbox,
            shell_count=1,
            shells=[],
            defects=defects,
            is_triangulated=True,
        )
        assert report.health_score < 1.0
        assert len(report.defects) == 1
        assert report.defects[0].defect_type == DefectType.boundary_edges

    def test_report_classification_matches_score(self, sample_bbox: BoundingBox):
        # Enough critical defects to drop below 0.3
        defects = [_defect(DefectType.boundary_edges, count=100)]
        report = build_report(
            mesh_path="/tmp/broken.stl",
            fmt="stl",
            detected_units="mm",
            vertex_count=100,
            face_count=200,
            bounding_box=sample_bbox,
            shell_count=1,
            shells=[],
            defects=defects,
            is_triangulated=True,
        )
        expected_classification = classify_health(report.health_score)
        assert report.classification == expected_classification
