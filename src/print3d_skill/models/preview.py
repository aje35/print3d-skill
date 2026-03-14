"""Preview rendering data models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ViewAngle:
    """Camera configuration for one panel of the composite preview."""

    name: str
    elevation: float
    azimuth: float


# Standard view angles for the 2x2 grid
FRONT = ViewAngle(name="front", elevation=0, azimuth=0)
SIDE = ViewAngle(name="side", elevation=0, azimuth=90)
TOP = ViewAngle(name="top", elevation=90, azimuth=0)
ISOMETRIC = ViewAngle(name="isometric", elevation=35, azimuth=45)

STANDARD_VIEWS = [FRONT, SIDE, TOP, ISOMETRIC]


@dataclass
class MeshSummary:
    """Quick stats about a rendered mesh."""

    face_count: int
    vertex_count: int
    bounding_box_mm: tuple[float, float, float]


@dataclass
class PreviewResult:
    """Output of the rendering pipeline."""

    image_path: str
    resolution: tuple[int, int]
    file_size_bytes: int
    views: list[ViewAngle]
    mesh_summary: MeshSummary
    warnings: list[str] = field(default_factory=list)
    render_time_seconds: float = 0.0
    timed_out: bool = False
