"""Model splitting with alignment features.

Splits a mesh along a plane into two watertight parts and optionally
adds alignment pins/holes at the cut boundary.
"""

from __future__ import annotations

import logging

import numpy as np
import trimesh

from print3d_skill.models.modify import (
    AlignmentFeature,
    AlignmentType,
    SplitParams,
)
from print3d_skill.modify.boolean import boolean_difference, boolean_union
from print3d_skill.modify.primitives import create_cylinder

logger = logging.getLogger(__name__)


def _axis_to_normal(axis: str) -> np.ndarray:
    """Convert axis string to unit normal vector."""
    normals = {
        "x": np.array([1.0, 0.0, 0.0]),
        "y": np.array([0.0, 1.0, 0.0]),
        "z": np.array([0.0, 0.0, 1.0]),
    }
    return normals[axis.lower()]


def split_mesh(
    mesh: trimesh.Trimesh,
    axis: str,
    offset_mm: float,
) -> tuple[trimesh.Trimesh, trimesh.Trimesh]:
    """Split a mesh along a plane into two watertight halves.

    Args:
        mesh: Input mesh.
        axis: "x", "y", or "z" - normal of the cutting plane.
        offset_mm: Position along the axis where the cut occurs.

    Returns:
        (bottom_part, top_part) relative to the cutting plane.

    Raises:
        ValueError: If cutting plane doesn't intersect the mesh.
    """
    normal = _axis_to_normal(axis)
    axis_idx = {"x": 0, "y": 1, "z": 2}[axis.lower()]

    # Compute plane origin
    bounds = mesh.bounds
    plane_origin = np.zeros(3)
    plane_origin[axis_idx] = bounds[0][axis_idx] + offset_mm

    # Validate that the plane intersects the mesh
    if plane_origin[axis_idx] <= bounds[0][axis_idx]:
        raise ValueError(
            f"Cutting plane at {axis}={plane_origin[axis_idx]:.1f}mm is below "
            f"the mesh minimum ({bounds[0][axis_idx]:.1f}mm). "
            f"Mesh bounds: {bounds[0][axis_idx]:.1f} to {bounds[1][axis_idx]:.1f}"
        )
    if plane_origin[axis_idx] >= bounds[1][axis_idx]:
        raise ValueError(
            f"Cutting plane at {axis}={plane_origin[axis_idx]:.1f}mm is above "
            f"the mesh maximum ({bounds[1][axis_idx]:.1f}mm). "
            f"Mesh bounds: {bounds[0][axis_idx]:.1f} to {bounds[1][axis_idx]:.1f}"
        )

    # Slice: bottom part (below the plane)
    bottom = trimesh.intersections.slice_mesh_plane(
        mesh, plane_normal=normal, plane_origin=plane_origin, cap=True
    )

    # Top part (above the plane) — flip the normal
    top = trimesh.intersections.slice_mesh_plane(
        mesh, plane_normal=-normal, plane_origin=plane_origin, cap=True
    )

    return bottom, top


def _find_pin_positions(
    mesh: trimesh.Trimesh,
    axis: str,
    offset_mm: float,
    num_pins: int = 2,
) -> list[np.ndarray]:
    """Find suitable positions for alignment pins on the cut face."""
    axis_idx = {"x": 0, "y": 1, "z": 2}[axis.lower()]
    bounds = mesh.bounds
    plane_pos = bounds[0][axis_idx] + offset_mm

    # Get the cross-section at the cut plane
    other_axes = [i for i in range(3) if i != axis_idx]

    # Place pins at positions that are well inside the cross-section
    center = (bounds[0] + bounds[1]) / 2
    dims = bounds[1] - bounds[0]

    positions = []
    if num_pins == 1:
        pos = center.copy()
        pos[axis_idx] = plane_pos
        positions.append(pos)
    else:
        # Place pins along the longest cross-section axis
        long_axis = other_axes[0] if dims[other_axes[0]] >= dims[other_axes[1]] else other_axes[1]
        spacing = dims[long_axis] * 0.3  # 30% from center

        for sign in [-1, 1]:
            pos = center.copy()
            pos[axis_idx] = plane_pos
            pos[long_axis] += sign * spacing
            positions.append(pos)

    return positions


def add_alignment_features(
    part_a: trimesh.Trimesh,
    part_b: trimesh.Trimesh,
    axis: str,
    offset_mm: float,
    pin_diameter: float = 4.0,
    pin_height: float = 6.0,
    pin_clearance: float = 0.3,
) -> tuple[trimesh.Trimesh, trimesh.Trimesh, list[AlignmentFeature]]:
    """Add alignment pins to part_a and matching holes to part_b.

    Returns (part_a_with_pins, part_b_with_holes, alignment_features).
    """
    positions = _find_pin_positions(
        trimesh.Trimesh(
            vertices=np.vstack([part_a.vertices, part_b.vertices]),
            faces=np.vstack([part_a.faces, part_b.faces + len(part_a.vertices)]),
            process=False,
        ),
        axis,
        offset_mm,
    )

    features: list[AlignmentFeature] = []

    for pos in positions:
        # Create pin cylinder
        pin = create_cylinder(pin_diameter, pin_height)
        # Create hole cylinder (pin + clearance)
        hole = create_cylinder(pin_diameter + 2 * pin_clearance, pin_height)

        # Orient pin along the split axis
        if axis.lower() == "x":
            rotation = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0])
            pin.apply_transform(rotation)
            hole.apply_transform(rotation)
        elif axis.lower() == "y":
            rotation = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
            pin.apply_transform(rotation)
            hole.apply_transform(rotation)
        # Z axis: no rotation needed (cylinder default is Z-aligned)

        # Position the pin: half in part_a, half in part_b
        pin.apply_translation(pos)
        hole.apply_translation(pos)

        # Boolean: add pin to part_a, subtract hole from part_b
        part_a = boolean_union(part_a, pin)
        part_b = boolean_difference(part_b, hole)

        # Record features
        features.append(AlignmentFeature(
            alignment_type=AlignmentType.PIN,
            position=tuple(pos.tolist()),
            diameter=pin_diameter,
            height=pin_height,
            clearance=0.0,
            part_index=0,
        ))
        features.append(AlignmentFeature(
            alignment_type=AlignmentType.HOLE,
            position=tuple(pos.tolist()),
            diameter=pin_diameter + 2 * pin_clearance,
            height=pin_height,
            clearance=pin_clearance,
            part_index=1,
        ))

    return part_a, part_b, features


def _check_split_warnings(
    mesh: trimesh.Trimesh,
    axis: str,
    offset_mm: float,
    pin_diameter: float,
) -> list[str]:
    """Generate warnings about split quality."""
    warnings: list[str] = []
    bounds = mesh.bounds
    dims = bounds[1] - bounds[0]
    axis_idx = {"x": 0, "y": 1, "z": 2}[axis.lower()]

    # Check if model fits standard print bed
    other_dims = [dims[i] for i in range(3) if i != axis_idx]
    if max(other_dims) <= 220 and dims[axis_idx] <= 220:
        warnings.append(
            f"Model already fits a standard 220x220mm print bed "
            f"(dimensions: {dims[0]:.0f}x{dims[1]:.0f}x{dims[2]:.0f}mm)"
        )

    # Check wall thickness at boundary
    cross_dims = [dims[i] for i in range(3) if i != axis_idx]
    min_cross = min(cross_dims)
    if min_cross < 2 * pin_diameter:
        warnings.append(
            f"Cross-section at cut boundary is thin ({min_cross:.1f}mm). "
            f"Alignment pins ({pin_diameter}mm diameter) may not fit reliably."
        )

    return warnings


def execute_split(
    mesh: trimesh.Trimesh,
    params: SplitParams,
) -> tuple[list[trimesh.Trimesh], list[str], list[AlignmentFeature]]:
    """Execute a split operation.

    Returns (parts, warnings, alignment_features).
    """
    warnings = _check_split_warnings(mesh, params.axis, params.offset_mm, params.pin_diameter)

    bottom, top = split_mesh(mesh, params.axis, params.offset_mm)

    alignment_features: list[AlignmentFeature] = []

    if params.add_alignment:
        bottom, top, alignment_features = add_alignment_features(
            bottom,
            top,
            params.axis,
            params.offset_mm,
            params.pin_diameter,
            params.pin_height,
            params.pin_clearance,
        )

    return [bottom, top], warnings, alignment_features
