"""Mesh repair pipeline.

Public API: repair_mesh()
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import trimesh

from print3d_skill.analysis import analyze_mesh
from print3d_skill.exceptions import MeshLoadError, RepairError, UnsupportedFormatError
from print3d_skill.export.formats import export_to_formats
from print3d_skill.models.analysis import MeshDefect, MeshHealthClassification
from print3d_skill.models.repair import RepairConfig, RepairSummary
from print3d_skill.repair.pipeline import run_pipeline

logger = logging.getLogger(__name__)


def repair_mesh(
    mesh_path: str,
    output_path: str | None = None,
    config: RepairConfig | None = None,
) -> RepairSummary:
    """Run the full repair pipeline on a mesh file.

    Args:
        mesh_path: Path to the input mesh file.
        output_path: Path for the repaired mesh output. If None, auto-generates.
        config: Optional repair configuration. If None, uses defaults.

    Returns:
        RepairSummary with analysis before/after, repairs applied, export paths.

    Raises:
        FileNotFoundError: mesh_path does not exist.
        UnsupportedFormatError: file format not supported.
        MeshLoadError: file is corrupt or unreadable.
        RepairError: repair pipeline encountered an unrecoverable error.
    """
    if not os.path.exists(mesh_path):
        raise FileNotFoundError(f"Mesh file not found: {mesh_path}")

    cfg = config or RepairConfig()

    # Step 1: Initial analysis
    initial_analysis = analyze_mesh(mesh_path, config=cfg)

    # Step 2: If print-ready, return immediately (idempotent)
    if initial_analysis.classification == MeshHealthClassification.print_ready:
        return RepairSummary(
            mesh_path=str(Path(mesh_path).resolve()),
            initial_analysis=initial_analysis,
            final_analysis=initial_analysis,
            repairs=[],
            total_defects_found=0,
            total_defects_fixed=0,
            remaining_defects=[],
        )

    # Step 3: Load mesh for repair
    try:
        mesh = trimesh.load(mesh_path, force="mesh")
    except Exception as e:
        raise MeshLoadError(f"Failed to load mesh for repair: {e}") from e

    # Get render function if previews enabled
    render_fn = None
    if cfg.render_previews:
        try:
            from print3d_skill.rendering import render_preview

            render_fn = render_preview
        except Exception:
            logger.debug("Rendering unavailable, skipping previews")

    # Step 4: Run repair pipeline
    try:
        repairs = run_pipeline(mesh, initial_analysis, cfg, render_fn=render_fn)
    except Exception as e:
        raise RepairError(f"Repair pipeline failed: {e}") from e

    # Step 5: Export repaired mesh to temp file for re-analysis
    output_dir = cfg.output_dir or str(Path(mesh_path).parent)
    stem = Path(mesh_path).stem
    if output_path:
        output_dir = str(Path(output_path).parent)
        stem = Path(output_path).stem

    export_paths = export_to_formats(mesh, output_dir, stem, cfg.export_formats)

    # Step 6: Re-analyze repaired mesh (use first exported file)
    first_export = next(iter(export_paths.values()), None)
    if first_export and os.path.exists(first_export):
        final_analysis = analyze_mesh(first_export, config=cfg)
    else:
        # Fallback: analyze from the in-memory mesh
        import tempfile

        tmp = os.path.join(tempfile.mkdtemp(), "repaired.stl")
        mesh.export(tmp, file_type="stl")
        final_analysis = analyze_mesh(tmp, config=cfg)

    # Step 7: Build summary
    total_found = len(initial_analysis.defects)
    remaining: list[MeshDefect] = final_analysis.defects
    total_fixed = total_found - len(remaining)

    classification_changed = (
        initial_analysis.classification != final_analysis.classification
    )

    severely_damaged_warning = None
    if initial_analysis.classification == MeshHealthClassification.severely_damaged:
        severely_damaged_warning = (
            "Mesh was severely damaged (health score: "
            f"{initial_analysis.health_score:.2f}). "
            "Best-effort repair was attempted but results may be incomplete."
        )

    return RepairSummary(
        mesh_path=str(Path(mesh_path).resolve()),
        initial_analysis=initial_analysis,
        final_analysis=final_analysis,
        repairs=repairs,
        total_defects_found=total_found,
        total_defects_fixed=max(total_fixed, 0),
        remaining_defects=remaining,
        export_paths=export_paths,
        classification_changed=classification_changed,
        severely_damaged_warning=severely_damaged_warning,
    )
