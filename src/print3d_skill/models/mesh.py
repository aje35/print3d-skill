"""Mesh data models for loaded 3D files."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass
class BoundingBox:
    """Axis-aligned bounding box of a mesh."""

    min_point: tuple[float, float, float]
    max_point: tuple[float, float, float]

    @property
    def dimensions(self) -> tuple[float, float, float]:
        return (
            self.max_point[0] - self.min_point[0],
            self.max_point[1] - self.min_point[1],
            self.max_point[2] - self.min_point[2],
        )

    @property
    def max_dimension(self) -> float:
        return max(self.dimensions)


@dataclass
class MeshFile:
    """Represents a loaded 3D model with extracted metadata."""

    path: str
    format: str
    vertices: NDArray[np.floating]
    faces: NDArray[np.integer]
    face_count: int
    vertex_count: int
    bounding_box: BoundingBox
    detected_units: str = "unknown"
    unit_warning: str | None = None
    file_size_bytes: int = 0
    face_normals: NDArray[np.floating] | None = None
