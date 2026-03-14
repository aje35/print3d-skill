"""Feature detection for scaling warnings (screw holes, etc.).

Detects standard metric screw hole diameters using circle-fitting on
boundary edge loops in the mesh.
"""

from __future__ import annotations

import logging

import numpy as np
import trimesh

from print3d_skill.models.modify import FeatureWarning, ScaleMode, ScaleParams

logger = logging.getLogger(__name__)

# ISO 273 clearance hole diameters (mm) with standard names
STANDARD_HOLES: list[tuple[str, float]] = [
    ("M2 clearance hole", 2.4),
    ("M2.5 clearance hole", 2.9),
    ("M3 clearance hole", 3.4),
    ("M4 clearance hole", 4.5),
    ("M5 clearance hole", 5.5),
    ("M6 clearance hole", 6.6),
    ("M8 clearance hole", 9.0),
    ("M10 clearance hole", 11.0),
]

TOLERANCE_MM = 0.3


def _fit_circle_to_points(points_2d: np.ndarray) -> tuple[float, float, float] | None:
    """Fit a circle to 2D points using algebraic least squares.

    Returns (cx, cy, radius) or None if fitting fails.
    """
    if len(points_2d) < 3:
        return None

    x = points_2d[:, 0]
    y = points_2d[:, 1]

    # Algebraic circle fit: minimize |Ax + By + C - (x^2 + y^2)|
    A = np.column_stack([x, y, np.ones_like(x)])
    b = x**2 + y**2
    try:
        result, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    except np.linalg.LinAlgError:
        return None

    cx = result[0] / 2.0
    cy = result[1] / 2.0
    r_sq = result[2] + cx**2 + cy**2
    if r_sq <= 0:
        return None
    return cx, cy, float(np.sqrt(r_sq))


def _find_circular_holes(mesh: trimesh.Trimesh) -> list[tuple[float, np.ndarray]]:
    """Find circular boundary loops in the mesh and return their diameters.

    Returns list of (diameter_mm, center_3d).
    """
    holes: list[tuple[float, np.ndarray]] = []

    # Get boundary edges (edges that belong to only one face)
    try:
        edges = mesh.edges_unique
        edge_faces = mesh.edges_unique_inverse
        face_count_per_edge = np.bincount(edge_faces)

        # Boundary edges are those shared by exactly 1 face
        boundary_mask = face_count_per_edge == 1
        boundary_edges = edges[boundary_mask[:len(edges)]]
    except Exception:
        return holes

    if len(boundary_edges) == 0:
        return holes

    # Build adjacency graph of boundary edges to find loops
    from collections import defaultdict

    adj: dict[int, list[int]] = defaultdict(list)
    for e in boundary_edges:
        adj[e[0]].append(e[1])
        adj[e[1]].append(e[0])

    visited: set[int] = set()
    loops: list[list[int]] = []

    for start in adj:
        if start in visited:
            continue
        loop: list[int] = []
        current = start
        while current not in visited:
            visited.add(current)
            loop.append(current)
            neighbors = [n for n in adj[current] if n not in visited]
            if not neighbors:
                break
            current = neighbors[0]
        if len(loop) >= 6:  # Need enough points for a reasonable circle fit
            loops.append(loop)

    verts = np.asarray(mesh.vertices)

    for loop in loops:
        points_3d = verts[loop]
        center = points_3d.mean(axis=0)

        # Project to local 2D plane for circle fitting
        # Find the plane normal from the points
        centered = points_3d - center
        try:
            _, _, vh = np.linalg.svd(centered)
            normal = vh[-1]
        except np.linalg.LinAlgError:
            continue

        # Create local 2D basis
        u = np.cross(normal, [1, 0, 0])
        if np.linalg.norm(u) < 1e-6:
            u = np.cross(normal, [0, 1, 0])
        u = u / np.linalg.norm(u)
        v = np.cross(normal, u)

        # Project to 2D
        points_2d = np.column_stack([centered @ u, centered @ v])

        fit = _fit_circle_to_points(points_2d)
        if fit is None:
            continue

        _, _, radius = fit
        diameter = radius * 2.0

        # Check how circular the loop actually is (residual check)
        distances = np.sqrt(points_2d[:, 0] ** 2 + points_2d[:, 1] ** 2)
        residual = np.std(distances) / (radius + 1e-10)
        if residual < 0.15:  # Within 15% residual = reasonably circular
            holes.append((diameter, center))

    return holes


def _match_standard_hole(diameter_mm: float) -> str | None:
    """Match a diameter to a standard metric screw hole size."""
    for name, std_diameter in STANDARD_HOLES:
        if abs(diameter_mm - std_diameter) <= TOLERANCE_MM:
            return name
    return None


def _compute_scale_factor(params: ScaleParams) -> float:
    """Compute effective uniform scale factor for feature warning."""
    if params.mode == ScaleMode.UNIFORM:
        return params.factor or 1.0
    if params.mode == ScaleMode.NON_UNIFORM:
        # Return average factor as approximation
        if params.factors:
            return sum(params.factors.values()) / len(params.factors)
        return 1.0
    # For dimension target, we don't know the factor without the mesh
    return 1.0


def detect_standard_holes(
    mesh: trimesh.Trimesh,
    params: ScaleParams,
) -> list[FeatureWarning]:
    """Detect standard screw holes and warn about size changes after scaling."""
    warnings: list[FeatureWarning] = []

    factor = _compute_scale_factor(params)
    if abs(factor - 1.0) < 1e-6:
        return warnings  # No scaling, no warnings needed

    holes = _find_circular_holes(mesh)

    for diameter, center in holes:
        match = _match_standard_hole(diameter)
        if match:
            new_diameter = diameter * factor
            new_match = _match_standard_hole(new_diameter)
            if new_match != match:
                warnings.append(
                    FeatureWarning(
                        feature_type="screw_hole",
                        original_dimension_mm=round(diameter, 2),
                        new_dimension_mm=round(new_diameter, 2),
                        standard_match=match,
                        message=(
                            f"{match} ({diameter:.1f}mm) will become "
                            f"{new_diameter:.1f}mm after scaling - "
                            f"no longer matches standard size"
                        ),
                    )
                )

    return warnings
