"""Mesh defect analysis engine.

Public API: analyze_mesh()
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import trimesh

from print3d_skill.analysis.detectors import (
    ALL_DETECTORS,
    detect_degenerate_faces,
    detect_duplicate_vertices,
    detect_excessive_poly_count,
)
from print3d_skill.analysis.report import build_report
from print3d_skill.exceptions import (
    MeshAnalysisError,
    MeshLoadError,
    UnsupportedFormatError,
)
from print3d_skill.models.analysis import MeshAnalysisReport, MeshDefect, ShellAnalysis
from print3d_skill.models.mesh import BoundingBox
from print3d_skill.models.repair import RepairConfig

SUPPORTED_FORMATS = {"stl", "3mf", "obj", "ply"}


def _detect_format(path: str) -> str:
    """Detect mesh format from file extension."""
    ext = Path(path).suffix.lower().lstrip(".")
    if ext in SUPPORTED_FORMATS:
        return ext
    raise UnsupportedFormatError(
        f"Unsupported file format '.{ext}'. "
        f"Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
    )


def _detect_units(bbox: BoundingBox) -> str:
    """Heuristic unit detection based on bounding box dimensions."""
    max_dim = bbox.max_dimension

    if max_dim < 0.5:
        return "meters"
    if max_dim > 2000:
        return "unknown"

    # Check for possible inches
    dims = bbox.dimensions
    inch_candidates = [d / 25.4 for d in dims if d > 0]
    common_inch_sizes = {0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0}
    inch_matches = sum(
        1
        for ic in inch_candidates
        if any(abs(ic - s) < 0.1 for s in common_inch_sizes)
    )
    if inch_matches >= 2:
        return "inches"

    return "mm"


def _load_mesh(path: str) -> trimesh.Trimesh:
    """Load a mesh file, auto-triangulating non-triangular faces."""
    try:
        loaded = trimesh.load(path, force="mesh")
    except Exception as e:
        raise MeshLoadError(f"Failed to load mesh '{path}': {e}") from e

    if not hasattr(loaded, "faces") or len(loaded.faces) == 0:
        raise MeshLoadError(f"Mesh '{path}' has no faces (empty mesh)")

    vertices = np.asarray(loaded.vertices)
    if not np.all(np.isfinite(vertices)):
        raise MeshLoadError(
            f"Mesh '{path}' contains NaN or infinite vertex coordinates"
        )

    return loaded


def _analyze_single_mesh(
    mesh: trimesh.Trimesh,
    config: RepairConfig | None = None,
) -> list[MeshDefect]:
    """Run all detectors on a single mesh, returning defects found."""
    cfg = config or RepairConfig()
    defects: list[MeshDefect] = []

    for detector in ALL_DETECTORS:
        # Pass config parameters to detectors that accept them
        if detector is detect_degenerate_faces:
            result = detector(mesh, area_threshold=cfg.degenerate_area_threshold)
        elif detector is detect_duplicate_vertices:
            result = detector(mesh, tolerance=cfg.vertex_merge_tolerance)
        elif detector is detect_excessive_poly_count:
            result = detector(mesh, max_count=cfg.max_poly_count)
        else:
            result = detector(mesh)

        if result is not None:
            defects.append(result)

    return defects


def analyze_mesh(
    mesh_path: str,
    config: RepairConfig | None = None,
) -> MeshAnalysisReport:
    """Analyze a mesh file for defects and produce a structured report.

    Args:
        mesh_path: Path to a mesh file (STL, 3MF, OBJ, PLY).
        config: Optional configuration for detection thresholds.

    Returns:
        MeshAnalysisReport with defects, health score, and classification.

    Raises:
        FileNotFoundError: mesh_path does not exist.
        UnsupportedFormatError: file format not in {stl, 3mf, obj, ply}.
        MeshLoadError: file is corrupt, truncated, or unreadable.
        MeshAnalysisError: analysis failed.
    """
    if not os.path.exists(mesh_path):
        raise FileNotFoundError(f"Mesh file not found: {mesh_path}")

    fmt = _detect_format(mesh_path)
    mesh = _load_mesh(mesh_path)

    # Check if auto-triangulation occurred (trimesh force="mesh" always triangulates)
    is_triangulated = True  # trimesh auto-triangulates on load

    # Compute bounding box
    vertices = np.asarray(mesh.vertices)
    bbox = BoundingBox(
        min_point=tuple(vertices.min(axis=0).tolist()),
        max_point=tuple(vertices.max(axis=0).tolist()),
    )

    # Detect units
    detected_units = _detect_units(bbox)

    # Split into shells
    try:
        shells_meshes = mesh.split()
    except Exception:
        shells_meshes = [mesh]

    if not isinstance(shells_meshes, list):
        shells_meshes = [shells_meshes]

    shell_count = len(shells_meshes) if shells_meshes else 1
    all_defects: list[MeshDefect] = []
    shell_analyses: list[ShellAnalysis] = []

    if shell_count <= 1:
        # Single body: analyze directly, don't populate shells list
        all_defects = _analyze_single_mesh(mesh, config)
    else:
        # Multi-body: analyze each shell independently
        for i, shell_mesh in enumerate(shells_meshes):
            shell_verts = np.asarray(shell_mesh.vertices)
            shell_bbox = BoundingBox(
                min_point=tuple(shell_verts.min(axis=0).tolist()),
                max_point=tuple(shell_verts.max(axis=0).tolist()),
            )
            shell_defects = _analyze_single_mesh(shell_mesh, config)
            all_defects.extend(shell_defects)

            shell_analyses.append(
                ShellAnalysis(
                    shell_index=i,
                    vertex_count=len(shell_mesh.vertices),
                    face_count=len(shell_mesh.faces),
                    bounding_box=shell_bbox,
                    is_watertight=shell_mesh.is_watertight,
                    defects=shell_defects,
                )
            )

    try:
        return build_report(
            mesh_path=str(Path(mesh_path).resolve()),
            fmt=fmt,
            detected_units=detected_units,
            vertex_count=len(mesh.vertices),
            face_count=len(mesh.faces),
            bounding_box=bbox,
            shell_count=shell_count,
            shells=shell_analyses,
            defects=all_defects,
            is_triangulated=is_triangulated,
        )
    except Exception as e:
        raise MeshAnalysisError(f"Failed to build analysis report: {e}") from e
