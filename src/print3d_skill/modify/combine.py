"""Model combining with alignment."""

from __future__ import annotations

import logging

import numpy as np
import trimesh

from print3d_skill.models.modify import CombineParams
from print3d_skill.modify.boolean import boolean_union

logger = logging.getLogger(__name__)


def _align_mesh(
    target: trimesh.Trimesh,
    other: trimesh.Trimesh,
    alignment: str,
    offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> trimesh.Trimesh:
    """Align `other` mesh relative to `target` using bounding box math."""
    result = other.copy()

    t_bounds = target.bounds
    t_center = (t_bounds[0] + t_bounds[1]) / 2
    o_bounds = result.bounds
    o_center = (o_bounds[0] + o_bounds[1]) / 2

    # Start by centering other on target's centroid
    translation = t_center - o_center

    if alignment == "center":
        pass  # Already centered
    elif alignment == "top":
        # Place other on top of target
        translation[2] = t_bounds[1][2] - o_bounds[0][2]
    elif alignment == "bottom":
        # Place other below target
        translation[2] = t_bounds[0][2] - o_bounds[1][2]
    elif alignment == "front":
        translation[1] = t_bounds[0][1] - o_bounds[1][1]
    elif alignment == "back":
        translation[1] = t_bounds[1][1] - o_bounds[0][1]
    elif alignment == "left":
        translation[0] = t_bounds[0][0] - o_bounds[1][0]
    elif alignment == "right":
        translation[0] = t_bounds[1][0] - o_bounds[0][0]

    # Apply additional offset
    translation += np.array(offset)
    result.apply_translation(translation)

    return result


def detect_scale_mismatch(meshes: list[trimesh.Trimesh]) -> list[str]:
    """Detect scale mismatches between meshes.

    Returns warnings if bounding box ratios exceed 10:1.
    """
    warnings: list[str] = []
    if len(meshes) < 2:
        return warnings

    volumes = []
    for m in meshes:
        dims = m.bounds[1] - m.bounds[0]
        vol = float(np.prod(dims))
        volumes.append(vol)

    max_vol = max(volumes)
    min_vol = max(min(volumes), 1e-10)

    if max_vol / min_vol > 1000:  # Volume ratio > 10:1 per axis cubed
        # Check if it looks like inches vs mm
        for i, m in enumerate(meshes):
            max_dim = float(np.max(m.bounds[1] - m.bounds[0]))
            if max_dim < 20:  # Might be in inches
                warnings.append(
                    f"Mesh {i} may be in inches (max dimension: {max_dim:.1f}). "
                    f"Consider scaling by 25.4 to convert to mm."
                )

    return warnings


def combine_meshes(
    target: trimesh.Trimesh,
    others: list[trimesh.Trimesh],
    alignment: str = "center",
    offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> trimesh.Trimesh:
    """Align and combine multiple meshes via boolean union."""
    result = target
    for other in others:
        aligned = _align_mesh(result, other, alignment, offset)
        result = boolean_union(result, aligned)
    return result


def execute_combine(
    mesh: trimesh.Trimesh,
    params: CombineParams,
) -> tuple[trimesh.Trimesh, list[str]]:
    """Execute a combine operation. Returns (result_mesh, warnings)."""
    warnings: list[str] = []

    # Load other meshes
    others: list[trimesh.Trimesh] = []
    for path in params.other_mesh_paths:
        other = trimesh.load(path, force="mesh")
        others.append(other)

    # Check for scale mismatches
    all_meshes = [mesh] + others
    mismatch_warnings = detect_scale_mismatch(all_meshes)
    warnings.extend(mismatch_warnings)

    # Combine
    result = combine_meshes(mesh, others, params.alignment, params.offset)

    return result, warnings
