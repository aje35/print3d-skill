"""Scaling operations (uniform, non-uniform, dimension-targeted)."""

from __future__ import annotations

import numpy as np
import trimesh

from print3d_skill.models.modify import ScaleMode, ScaleParams


def scale_uniform(mesh: trimesh.Trimesh, factor: float) -> trimesh.Trimesh:
    """Scale mesh uniformly by a factor (e.g., 1.2 = 120%)."""
    result = mesh.copy()
    matrix = np.eye(4)
    matrix[0, 0] = factor
    matrix[1, 1] = factor
    matrix[2, 2] = factor
    result.apply_transform(matrix)
    return result


def scale_non_uniform(
    mesh: trimesh.Trimesh, factors: dict[str, float]
) -> trimesh.Trimesh:
    """Scale mesh non-uniformly per axis."""
    result = mesh.copy()
    matrix = np.eye(4)
    matrix[0, 0] = factors.get("x", 1.0)
    matrix[1, 1] = factors.get("y", 1.0)
    matrix[2, 2] = factors.get("z", 1.0)
    result.apply_transform(matrix)
    return result


def scale_to_dimension(
    mesh: trimesh.Trimesh,
    axis: str,
    target_mm: float,
    proportional: bool = True,
) -> trimesh.Trimesh:
    """Scale mesh so that a specific axis reaches a target dimension."""
    bounds = mesh.bounds
    dims = bounds[1] - bounds[0]
    axis_map = {"x": 0, "y": 1, "z": 2}
    idx = axis_map.get(axis.lower())
    if idx is None:
        raise ValueError(f"Invalid axis '{axis}', must be 'x', 'y', or 'z'")

    current = dims[idx]
    if current < 1e-10:
        raise ValueError(f"Mesh has zero extent along {axis} axis, cannot scale")

    factor = target_mm / current

    if proportional:
        return scale_uniform(mesh, factor)

    factors = {"x": 1.0, "y": 1.0, "z": 1.0}
    factors[axis.lower()] = factor
    return scale_non_uniform(mesh, factors)


def execute_scale(
    mesh: trimesh.Trimesh,
    params: ScaleParams,
) -> tuple[trimesh.Trimesh, list[str]]:
    """Execute a scaling operation. Returns (result_mesh, warnings)."""
    warnings: list[str] = []

    if params.mode == ScaleMode.UNIFORM:
        result = scale_uniform(mesh, params.factor)
    elif params.mode == ScaleMode.NON_UNIFORM:
        result = scale_non_uniform(mesh, params.factors)
    elif params.mode == ScaleMode.DIMENSION_TARGET:
        result = scale_to_dimension(
            mesh, params.target_axis, params.target_value_mm, params.proportional
        )
    else:
        raise ValueError(f"Unknown scale mode: {params.mode}")

    return result, warnings
