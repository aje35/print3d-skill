"""Composed repair pipeline with ordered strategy execution."""

from __future__ import annotations

import logging
import os
import tempfile

import trimesh

from print3d_skill.models.analysis import (
    MeshAnalysisReport,
    MeshDefect,
    MeshHealthClassification,
)
from print3d_skill.models.repair import RepairConfig, RepairResult

from .strategies import (
    strategy_decimate,
    strategy_fill_holes,
    strategy_fix_normals,
    strategy_merge_vertices,
    strategy_remove_degenerates,
    strategy_remove_duplicates,
)

logger = logging.getLogger(__name__)

# Ordered repair pipeline: per FR-024
REPAIR_ORDER = [
    ("merge_vertices", strategy_merge_vertices),
    ("remove_degenerates", strategy_remove_degenerates),
    ("remove_duplicates", strategy_remove_duplicates),
    ("fill_holes", strategy_fill_holes),
    ("fix_normals", strategy_fix_normals),
]


def run_pipeline(
    mesh: trimesh.Trimesh,
    initial_analysis: MeshAnalysisReport,
    config: RepairConfig,
    render_fn: object | None = None,
) -> list[RepairResult]:
    """Execute the repair pipeline in defined order.

    Args:
        mesh: The trimesh object to repair (modified in-place).
        initial_analysis: Analysis report before repair.
        config: Repair configuration.
        render_fn: Optional callable(mesh, output_path) for previews.

    Returns:
        List of RepairResult for each step executed.
    """
    results: list[RepairResult] = []

    # Log severely damaged warning
    if initial_analysis.classification == MeshHealthClassification.severely_damaged:
        logger.warning(
            "Mesh is severely damaged (score: %.2f). "
            "Attempting best-effort repair — results may be incomplete.",
            initial_analysis.health_score,
        )

    for step_name, strategy_fn in REPAIR_ORDER:
        before_preview_path = None
        after_preview_path = None

        # Render before preview if configured
        if config.render_previews and render_fn is not None:
            try:
                before_path = os.path.join(
                    tempfile.mkdtemp(prefix="repair_preview_"),
                    f"before_{step_name}.png",
                )
                _render_mesh(mesh, before_path, render_fn)
                before_preview_path = before_path
            except Exception:
                logger.debug("Failed to render before preview for %s", step_name)

        # Execute repair strategy
        if step_name in ("merge_vertices", "remove_degenerates"):
            result = strategy_fn(mesh, config)
        else:
            result = strategy_fn(mesh)

        # Update preview paths
        result.before_preview_path = before_preview_path

        # Render after preview if configured
        if config.render_previews and render_fn is not None:
            try:
                after_path = os.path.join(
                    tempfile.mkdtemp(prefix="repair_preview_"),
                    f"after_{step_name}.png",
                )
                _render_mesh(mesh, after_path, render_fn)
                result.after_preview_path = after_path
            except Exception:
                logger.debug("Failed to render after preview for %s", step_name)

        results.append(result)

    # Handle decimation if configured
    if config.decimation_target is not None:
        result = strategy_decimate(mesh, config.decimation_target)
        results.append(result)

    return results


def _render_mesh(
    mesh: trimesh.Trimesh,
    output_path: str,
    render_fn: object,
) -> None:
    """Render a mesh to a preview image using the provided render function."""
    # Export mesh to a temp file for the renderer
    tmp_path = os.path.join(
        tempfile.mkdtemp(prefix="repair_render_"),
        "temp_mesh.stl",
    )
    mesh.export(tmp_path, file_type="stl")
    render_fn(tmp_path, output_path)  # type: ignore[operator]
