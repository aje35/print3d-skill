"""Format-specific mesh exporters using trimesh."""

from __future__ import annotations

import os
from pathlib import Path

import trimesh


def export_to_formats(
    mesh: trimesh.Trimesh,
    output_dir: str,
    stem: str,
    formats: list[str],
) -> dict[str, str]:
    """Export a mesh to one or more formats.

    Args:
        mesh: The trimesh object to export.
        output_dir: Directory for output files.
        stem: Base filename without extension.
        formats: List of format strings (e.g., ["stl", "3mf"]).

    Returns:
        Dict mapping format name to absolute file path.
    """
    os.makedirs(output_dir, exist_ok=True)
    paths: dict[str, str] = {}

    for fmt in formats:
        ext = fmt.lower().lstrip(".")
        filename = f"{stem}.{ext}"
        output_path = os.path.join(output_dir, filename)

        mesh.export(output_path, file_type=ext)
        paths[ext] = str(Path(output_path).resolve())

    return paths
