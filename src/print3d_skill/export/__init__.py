"""Mesh export pipeline.

Public API: export_mesh()
"""

from __future__ import annotations

import os
from pathlib import Path

import trimesh

from print3d_skill.analysis import analyze_mesh
from print3d_skill.exceptions import ExportError, MeshLoadError, UnsupportedFormatError
from print3d_skill.export.formats import export_to_formats
from print3d_skill.models.export import ExportResult


def export_mesh(
    mesh_path: str,
    output_dir: str | None = None,
    formats: list[str] | None = None,
) -> ExportResult:
    """Export a mesh to one or more formats.

    Args:
        mesh_path: Path to the mesh file to export.
        output_dir: Directory for output files. If None, uses input file's dir.
        formats: Output formats (e.g., ["stl", "3mf"]). Defaults to ["stl", "3mf"].

    Returns:
        ExportResult with paths to exported files and analysis.

    Raises:
        FileNotFoundError: mesh_path does not exist.
        UnsupportedFormatError: input format not supported.
        MeshLoadError: file is corrupt or unreadable.
        ExportError: export failed.
    """
    if not os.path.exists(mesh_path):
        raise FileNotFoundError(f"Mesh file not found: {mesh_path}")

    out_dir = output_dir or str(Path(mesh_path).parent)
    out_formats = formats or ["stl", "3mf"]
    stem = Path(mesh_path).stem

    # Analyze the input mesh
    analysis = analyze_mesh(mesh_path)

    # Load mesh for export
    try:
        mesh = trimesh.load(mesh_path, force="mesh")
    except Exception as e:
        raise MeshLoadError(f"Failed to load mesh for export: {e}") from e

    # Export to requested formats
    try:
        paths = export_to_formats(mesh, out_dir, stem, out_formats)
    except Exception as e:
        raise ExportError(f"Export failed: {e}") from e

    return ExportResult(
        paths=paths,
        repair_summary=None,
        analysis_report=analysis,
    )
