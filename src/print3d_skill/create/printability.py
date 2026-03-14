"""FDM printability validation checks.

Four checks: wall thickness, overhang angle, bridge distance, bed adhesion.
All use trimesh + numpy for mesh-level analysis.
"""

from __future__ import annotations

import os

import numpy as np
import trimesh

from print3d_skill.models.create import (
    CreateConfig,
    PrintabilityReport,
    PrintabilityWarning,
)


def validate_printability(
    mesh_path: str,
    config: CreateConfig | None = None,
) -> PrintabilityReport:
    """Validate a mesh against FDM printability rules.

    Runs all 4 checks: wall thickness, overhangs, bridges, bed adhesion.

    Args:
        mesh_path: Path to a compiled mesh file (STL, 3MF, OBJ, PLY).
        config: Thresholds for validation rules. Uses defaults if None.

    Returns:
        PrintabilityReport with warnings and pass/fail status.

    Raises:
        FileNotFoundError: mesh_path does not exist.
    """
    if not os.path.exists(mesh_path):
        raise FileNotFoundError(f"Mesh file not found: {mesh_path}")

    if config is None:
        config = CreateConfig()

    mesh = trimesh.load(mesh_path, force="mesh")

    warnings: list[PrintabilityWarning] = []
    total_checks = 4
    passed_checks = 0

    # Check 1: Wall thickness
    wall_result = _check_wall_thickness(mesh, config)
    if wall_result is None:
        passed_checks += 1
        wall_min = None
    else:
        warnings.append(wall_result[0])
        wall_min = wall_result[1]

    # Check 2: Overhang angle
    overhang_result = _check_overhangs(mesh, config)
    if overhang_result is None:
        passed_checks += 1
        max_overhang = None
    else:
        warnings.append(overhang_result[0])
        max_overhang = overhang_result[1]

    # Check 3: Bridge distance
    bridge_result = _check_bridges(mesh, config)
    if bridge_result is None:
        passed_checks += 1
        max_bridge = None
    else:
        warnings.append(bridge_result[0])
        max_bridge = bridge_result[1]

    # Check 4: Bed adhesion
    adhesion_result = _check_bed_adhesion(mesh, config)
    if adhesion_result is None:
        passed_checks += 1
        bed_area = None
    else:
        warnings.append(adhesion_result[0])
        bed_area = adhesion_result[1]

    has_errors = any(w.severity == "error" for w in warnings)

    return PrintabilityReport(
        mesh_path=mesh_path,
        config=config,
        warnings=warnings,
        is_printable=not has_errors,
        total_checks=total_checks,
        passed_checks=passed_checks,
        wall_thickness_min=wall_min,
        max_overhang_angle_found=max_overhang,
        max_bridge_distance_found=max_bridge,
        bed_adhesion_area=bed_area,
    )


def _check_wall_thickness(
    mesh: trimesh.Trimesh,
    config: CreateConfig,
) -> tuple[PrintabilityWarning, float] | None:
    """Check minimum wall thickness via ray casting.

    For a sample of faces, shoot a ray inward (negative normal) and
    measure distance to the nearest opposing face.

    Returns None if all walls are thick enough, or (warning, min_thickness).
    """
    if len(mesh.faces) == 0:
        return None

    normals = mesh.face_normals
    centers = mesh.triangles_center

    # Sample up to 500 faces for performance
    n_faces = len(mesh.faces)
    if n_faces > 500:
        indices = np.random.default_rng(42).choice(n_faces, 500, replace=False)
    else:
        indices = np.arange(n_faces)

    sample_centers = centers[indices]
    sample_normals = normals[indices]

    # Offset origins slightly inward to avoid self-intersection
    origins = sample_centers - sample_normals * 0.01
    directions = -sample_normals

    try:
        locations, index_ray, _ = mesh.ray.intersects_location(
            ray_origins=origins,
            ray_directions=directions,
        )
    except Exception:
        return None

    if len(locations) == 0:
        return None

    # Compute distances for each ray hit
    distances = np.linalg.norm(locations - origins[index_ray], axis=1)

    # Find the minimum distance per ray (closest opposing face)
    min_thickness = float("inf")
    for i in range(len(indices)):
        ray_mask = index_ray == i
        if ray_mask.any():
            ray_dists = distances[ray_mask]
            min_dist = float(ray_dists.min())
            if min_dist < min_thickness:
                min_thickness = min_dist

    if min_thickness == float("inf"):
        return None

    if min_thickness >= config.min_wall_thickness:
        return None

    thin_count = 0
    for i in range(len(indices)):
        ray_mask = index_ray == i
        if ray_mask.any():
            if float(distances[ray_mask].min()) < config.min_wall_thickness:
                thin_count += 1

    return (
        PrintabilityWarning(
            rule="min_wall_thickness",
            severity="error",
            measured_value=round(min_thickness, 2),
            threshold=config.min_wall_thickness,
            location="Thin wall region detected",
            suggestion=(
                f"Wall thickness {min_thickness:.2f}mm is below "
                f"minimum {config.min_wall_thickness}mm for "
                f"{config.nozzle_diameter}mm nozzle — increase to "
                f"at least {config.min_wall_thickness}mm"
            ),
            affected_face_count=thin_count,
        ),
        min_thickness,
    )


def _check_overhangs(
    mesh: trimesh.Trimesh,
    config: CreateConfig,
) -> tuple[PrintabilityWarning, float] | None:
    """Check for overhang angles exceeding the threshold.

    Computes angle between each face normal and the Z-up build direction.
    Faces pointing downward more than max_overhang_angle from vertical
    are flagged.

    Returns None if no overhangs exceed threshold, or (warning, max_angle).
    """
    if len(mesh.faces) == 0:
        return None

    normals = mesh.face_normals
    z_up = np.array([0.0, 0.0, 1.0])

    # Dot product with Z-up: 1 = pointing up, -1 = pointing down
    dots = np.dot(normals, z_up)

    # Angle from vertical (0 = pointing up, 180 = pointing down)
    angles_from_vertical = np.degrees(np.arccos(np.clip(dots, -1.0, 1.0)))

    # Overhang angle is measured from vertical: faces > 90+threshold are overhangs
    # A face at 135° from vertical = 45° overhang (pointing 45° past horizontal)
    overhang_threshold = 90.0 + config.max_overhang_angle
    overhang_mask = angles_from_vertical > overhang_threshold

    if not overhang_mask.any():
        return None

    max_angle = float(angles_from_vertical[overhang_mask].max())
    overhang_degrees = max_angle - 90.0
    overhang_count = int(overhang_mask.sum())

    return (
        PrintabilityWarning(
            rule="max_overhang_angle",
            severity="warning",
            measured_value=round(overhang_degrees, 1),
            threshold=config.max_overhang_angle,
            location=f"{overhang_count} faces with excessive overhang",
            suggestion=(
                f"Overhang of {overhang_degrees:.1f}° exceeds "
                f"{config.max_overhang_angle}° limit — add supports "
                f"or redesign angle to {config.max_overhang_angle}° or less"
            ),
            affected_face_count=overhang_count,
        ),
        overhang_degrees,
    )


def _check_bridges(
    mesh: trimesh.Trimesh,
    config: CreateConfig,
) -> tuple[PrintabilityWarning, float] | None:
    """Check for unsupported bridging spans.

    Identifies horizontal downward-facing faces and checks if they are
    supported from below within the bridge distance threshold.

    Returns None if no excessive bridges found, or (warning, max_span).
    """
    if len(mesh.faces) == 0:
        return None

    normals = mesh.face_normals
    centers = mesh.triangles_center

    # Find faces pointing mostly downward (normal Z < -0.7 ≈ >45° from horizontal)
    downward_mask = normals[:, 2] < -0.7

    if not downward_mask.any():
        return None

    down_centers = centers[downward_mask]
    down_directions = np.tile([0.0, 0.0, -1.0], (len(down_centers), 1))

    # Offset origins slightly downward to avoid self-hit
    origins = down_centers + np.array([0.0, 0.0, -0.01])

    try:
        locations, index_ray, _ = mesh.ray.intersects_location(
            ray_origins=origins,
            ray_directions=down_directions,
        )
    except Exception:
        return None

    # Find unsupported faces (no geometry below within threshold)
    hit_rays = set(index_ray.tolist())
    n_down = len(down_centers)
    max_span = 0.0
    unsupported_count = 0

    for i in range(n_down):
        if i not in hit_rays:
            # No geometry below at all — fully unsupported
            unsupported_count += 1
            # Use mesh bounds as approximate span
            span = float(mesh.bounds[1][2] - mesh.bounds[0][2])
            max_span = max(max_span, span)
        else:
            # Check distance to nearest support
            ray_mask = index_ray == i
            if ray_mask.any():
                dists = np.abs(locations[ray_mask][:, 2] - origins[i][2])
                min_dist = float(dists.min())
                if min_dist > config.max_bridge_distance:
                    unsupported_count += 1
                    max_span = max(max_span, min_dist)

    if unsupported_count == 0 or max_span <= config.max_bridge_distance:
        return None

    return (
        PrintabilityWarning(
            rule="max_bridge_distance",
            severity="warning",
            measured_value=round(max_span, 1),
            threshold=config.max_bridge_distance,
            location=f"{unsupported_count} downward-facing regions unsupported",
            suggestion=(
                f"Bridge span of {max_span:.1f}mm exceeds "
                f"{config.max_bridge_distance}mm limit — reduce span "
                f"or add intermediate supports"
            ),
            affected_face_count=unsupported_count,
        ),
        max_span,
    )


def _check_bed_adhesion(
    mesh: trimesh.Trimesh,
    config: CreateConfig,
) -> tuple[PrintabilityWarning, float] | None:
    """Estimate bed contact area.

    Finds the lowest Z coordinate, selects faces within 0.1mm of it,
    and sums their projected XY area.

    Returns None if adhesion is sufficient, or (warning, contact_area).
    """
    if len(mesh.faces) == 0:
        return None

    z_min = float(mesh.vertices[:, 2].min())
    tolerance = 0.1  # one layer height

    # Find faces where ALL vertices are near the bottom
    face_vertices = mesh.vertices[mesh.faces]  # (N, 3, 3)
    face_z_max = face_vertices[:, :, 2].max(axis=1)  # max Z per face
    bottom_mask = face_z_max <= z_min + tolerance

    if not bottom_mask.any():
        # No faces touching the bed
        contact_area = 0.0
    else:
        # Sum the area of bottom faces
        contact_area = float(mesh.area_faces[bottom_mask].sum())

    if contact_area >= config.min_bed_adhesion_area:
        return None

    return (
        PrintabilityWarning(
            rule="min_bed_adhesion_area",
            severity="warning" if contact_area > 0 else "error",
            measured_value=round(contact_area, 1),
            threshold=config.min_bed_adhesion_area,
            location="Bottom face of model",
            suggestion=(
                f"Bed contact area {contact_area:.1f}mm² is below "
                f"minimum {config.min_bed_adhesion_area}mm² — add a "
                f"brim or increase the base footprint"
            ),
            affected_face_count=int(bottom_mask.sum()),
        ),
        contact_area,
    )
