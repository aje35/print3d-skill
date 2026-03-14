"""Boolean operations (union, difference, intersection) via manifold3d.

Falls back to trimesh.boolean when manifold3d is unavailable.
"""

from __future__ import annotations

import logging

import numpy as np
import trimesh

from print3d_skill.models.modify import BooleanParams, BooleanType

logger = logging.getLogger(__name__)

_HAS_MANIFOLD = False
try:
    import manifold3d
    _HAS_MANIFOLD = True
except ImportError:
    logger.debug("manifold3d not available, boolean ops will use trimesh fallback")


def _trimesh_to_manifold(mesh: trimesh.Trimesh) -> manifold3d.Manifold:
    """Convert a trimesh.Trimesh to a manifold3d.Manifold."""
    verts = np.asarray(mesh.vertices, dtype=np.float32)
    faces = np.asarray(mesh.faces, dtype=np.int32)
    m_mesh = manifold3d.Mesh(vert_properties=verts, tri_verts=faces)
    return manifold3d.Manifold(m_mesh)


def _manifold_to_trimesh(manifold: manifold3d.Manifold) -> trimesh.Trimesh:
    """Convert a manifold3d.Manifold back to trimesh.Trimesh."""
    m_mesh = manifold.to_mesh()
    verts = m_mesh.vert_properties[:, :3]
    faces = m_mesh.tri_verts
    return trimesh.Trimesh(vertices=verts, faces=faces, process=True)


def boolean_union(mesh_a: trimesh.Trimesh, mesh_b: trimesh.Trimesh) -> trimesh.Trimesh:
    """Perform boolean union using manifold3d (with trimesh fallback)."""
    if _HAS_MANIFOLD:
        ma = _trimesh_to_manifold(mesh_a)
        mb = _trimesh_to_manifold(mesh_b)
        result = ma + mb
        return _manifold_to_trimesh(result)
    return trimesh.boolean.union([mesh_a, mesh_b], engine="blender")


def boolean_difference(
    mesh_a: trimesh.Trimesh, mesh_b: trimesh.Trimesh
) -> trimesh.Trimesh:
    """Perform boolean difference (A - B) using manifold3d."""
    if _HAS_MANIFOLD:
        ma = _trimesh_to_manifold(mesh_a)
        mb = _trimesh_to_manifold(mesh_b)
        result = ma - mb
        return _manifold_to_trimesh(result)
    return trimesh.boolean.difference([mesh_a, mesh_b], engine="blender")


def boolean_intersection(
    mesh_a: trimesh.Trimesh, mesh_b: trimesh.Trimesh
) -> trimesh.Trimesh:
    """Perform boolean intersection using manifold3d."""
    if _HAS_MANIFOLD:
        ma = _trimesh_to_manifold(mesh_a)
        mb = _trimesh_to_manifold(mesh_b)
        result = ma ^ mb
        return _manifold_to_trimesh(result)
    return trimesh.boolean.intersection([mesh_a, mesh_b], engine="blender")


def _check_empty_result(mesh: trimesh.Trimesh, op_name: str) -> list[str]:
    """Check if a boolean result produced an empty or degenerate mesh."""
    warnings: list[str] = []
    if len(mesh.faces) == 0 or len(mesh.vertices) == 0:
        warnings.append(
            f"Boolean {op_name} produced empty result: "
            "meshes may not overlap or operand is fully contained"
        )
    elif hasattr(mesh, "volume") and abs(mesh.volume) < 1e-10:
        warnings.append(
            f"Boolean {op_name} produced near-zero volume result"
        )
    return warnings


def execute_boolean(
    mesh: trimesh.Trimesh,
    params: BooleanParams,
) -> tuple[trimesh.Trimesh, list[str], bool]:
    """Execute a boolean operation with auto-repair and empty detection.

    Returns (result_mesh, warnings, repair_performed).
    """
    warnings: list[str] = []
    repair_performed = False

    # Resolve the tool mesh
    if params.tool_mesh_path:
        tool = trimesh.load(params.tool_mesh_path, force="mesh")
    elif params.tool_primitive:
        from print3d_skill.modify.primitives import create_primitive
        tool = create_primitive(params.tool_primitive)
    else:
        raise ValueError("BooleanParams has neither tool_mesh_path nor tool_primitive")

    # Auto-repair: check if either mesh needs repair before boolean
    for label, m in [("target", mesh), ("tool", tool)]:
        if not m.is_watertight:
            logger.info("Auto-repairing %s mesh before boolean", label)
            try:
                import os
                import tempfile

                from print3d_skill.repair import repair_mesh as _repair

                tmp_path = os.path.join(tempfile.mkdtemp(), f"{label}.stl")
                m.export(tmp_path, file_type="stl")
                summary = _repair(tmp_path)
                if summary.export_paths:
                    repaired_path = next(iter(summary.export_paths.values()))
                    repaired = trimesh.load(repaired_path, force="mesh")
                    if label == "target":
                        mesh = repaired
                    else:
                        tool = repaired
                    repair_performed = True
                    warnings.append(f"Auto-repaired {label} mesh before boolean")
            except Exception as e:
                logger.warning("Auto-repair of %s mesh failed: %s", label, e)
                warnings.append(f"Auto-repair of {label} mesh failed: {e}")

    # Perform the boolean operation
    ops = {
        BooleanType.UNION: boolean_union,
        BooleanType.DIFFERENCE: boolean_difference,
        BooleanType.INTERSECTION: boolean_intersection,
    }
    op_func = ops[params.boolean_type]
    result = op_func(mesh, tool)

    # Check for empty result
    empty_warnings = _check_empty_result(result, params.boolean_type.value)
    warnings.extend(empty_warnings)

    return result, warnings, repair_performed
