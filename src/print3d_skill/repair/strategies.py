"""Individual mesh repair strategy functions.

Each strategy targets a specific defect type and returns a RepairResult
describing what was done.
"""

from __future__ import annotations

import numpy as np
import trimesh

from print3d_skill.models.analysis import DefectType
from print3d_skill.models.repair import RepairConfig, RepairResult, RepairStrategy


def strategy_merge_vertices(
    mesh: trimesh.Trimesh, config: RepairConfig
) -> RepairResult:
    """Merge duplicate vertices within configurable tolerance."""
    original_count = len(mesh.vertices)

    # Use trimesh's grouping for custom tolerance merging
    mesh.merge_vertices(merge_tex=True, merge_norm=True)

    # If default merge wasn't aggressive enough, try with custom tolerance
    if config.vertex_merge_tolerance > 1e-8:
        # More aggressive: use scipy for custom tolerance
        from scipy.spatial import cKDTree

        tree = cKDTree(mesh.vertices)
        pairs = tree.query_pairs(r=config.vertex_merge_tolerance)
        if pairs:
            # Build mapping: for each pair, map the second to the first
            remap = np.arange(len(mesh.vertices))
            for i, j in pairs:
                remap[max(i, j)] = min(i, j)
            # Propagate chains
            for i in range(len(remap)):
                while remap[i] != remap[remap[i]]:
                    remap[i] = remap[remap[i]]
            # Remap faces
            mesh.faces = remap[mesh.faces]
            mesh.remove_unreferenced_vertices()

    merged_count = original_count - len(mesh.vertices)
    return RepairResult(
        strategy=RepairStrategy.merge_vertices,
        defect_type=DefectType.duplicate_vertices,
        success=merged_count > 0,
        elements_affected=merged_count,
        description=f"Merged {merged_count} duplicate vertices (tolerance: {config.vertex_merge_tolerance})",
    )


def strategy_remove_degenerates(
    mesh: trimesh.Trimesh, config: RepairConfig
) -> RepairResult:
    """Remove zero-area and near-zero-area faces."""
    original_count = len(mesh.faces)

    # Remove degenerate faces: keep only faces with area >= threshold
    areas = mesh.area_faces
    keep_mask = areas >= config.degenerate_area_threshold
    if not np.all(keep_mask):
        mesh.update_faces(keep_mask)

    removed_count = original_count - len(mesh.faces)
    return RepairResult(
        strategy=RepairStrategy.remove_degenerates,
        defect_type=DefectType.degenerate_faces,
        success=removed_count > 0,
        elements_affected=removed_count,
        description=f"Removed {removed_count} degenerate faces (area threshold: {config.degenerate_area_threshold})",
    )


def strategy_remove_duplicates(mesh: trimesh.Trimesh) -> RepairResult:
    """Remove duplicate faces (identical vertex index triples)."""
    original_count = len(mesh.faces)

    # Find unique faces by sorting vertex indices and deduplicating
    sorted_faces = np.sort(mesh.faces, axis=1)
    _, unique_idx = np.unique(sorted_faces, axis=0, return_index=True)
    if len(unique_idx) < original_count:
        keep_mask = np.zeros(original_count, dtype=bool)
        keep_mask[unique_idx] = True
        mesh.update_faces(keep_mask)

    removed_count = original_count - len(mesh.faces)
    return RepairResult(
        strategy=RepairStrategy.remove_duplicates,
        defect_type=DefectType.duplicate_faces,
        success=removed_count > 0,
        elements_affected=removed_count,
        description=f"Removed {removed_count} duplicate faces",
    )


def strategy_fill_holes(mesh: trimesh.Trimesh) -> RepairResult:
    """Fill boundary edge holes using fan triangulation."""
    # Count boundary edges before
    from collections import Counter

    def count_boundary_edges(m: trimesh.Trimesh) -> int:
        edges = m.edges_sorted
        edge_count: Counter[tuple[int, int]] = Counter()
        for edge in edges:
            edge_count[tuple(edge)] += 1
        return sum(1 for c in edge_count.values() if c == 1)

    before = count_boundary_edges(mesh)

    trimesh.repair.fill_holes(mesh)

    after = count_boundary_edges(mesh)
    filled = before - after

    return RepairResult(
        strategy=RepairStrategy.fill_holes,
        defect_type=DefectType.boundary_edges,
        success=filled > 0,
        elements_affected=filled,
        description=f"Filled {filled} boundary holes ({before} edges before, {after} after)",
    )


def strategy_fix_normals(mesh: trimesh.Trimesh) -> RepairResult:
    """Reconcile face normals to face outward consistently."""
    # trimesh.repair.fix_normals reconciles winding and outward orientation
    trimesh.repair.fix_normals(mesh)
    trimesh.repair.fix_winding(mesh)

    # Count is approximate — we fixed all faces
    return RepairResult(
        strategy=RepairStrategy.fix_normals,
        defect_type=DefectType.inconsistent_normals,
        success=True,
        elements_affected=len(mesh.faces),
        description=f"Reconciled {len(mesh.faces)} face normals",
    )


def strategy_decimate(
    mesh: trimesh.Trimesh, target_faces: int
) -> RepairResult:
    """Reduce polygon count using quadric error metric decimation."""
    original_count = len(mesh.faces)

    if original_count <= target_faces:
        return RepairResult(
            strategy=RepairStrategy.decimate,
            defect_type=DefectType.excessive_poly_count,
            success=False,
            elements_affected=0,
            description=f"Face count {original_count} already below target {target_faces}",
        )

    decimated = mesh.simplify_quadric_decimation(target_faces)

    # Replace mesh data in-place
    mesh.vertices = decimated.vertices
    mesh.faces = decimated.faces

    reduced = original_count - len(mesh.faces)
    return RepairResult(
        strategy=RepairStrategy.decimate,
        defect_type=DefectType.excessive_poly_count,
        success=reduced > 0,
        elements_affected=reduced,
        description=f"Decimated from {original_count} to {len(mesh.faces)} faces (target: {target_faces})",
    )
