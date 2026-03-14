"""Before/after visual comparison for modifications."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import trimesh

from print3d_skill.models.preview import STANDARD_VIEWS, ViewAngle
from print3d_skill.rendering import render_preview

logger = logging.getLogger(__name__)


def render_before_after(
    mesh_before_path: str,
    mesh_after_path: str,
    output_dir: str,
    stem: str = "comparison",
) -> tuple[str, str]:
    """Render before/after previews with matching camera angles.

    Returns (before_preview_path, after_preview_path).
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    before_path = str(out / f"{stem}_before.png")
    after_path = str(out / f"{stem}_after.png")

    render_preview(mesh_before_path, before_path)
    render_preview(mesh_after_path, after_path)

    return before_path, after_path


def render_multiple_after(
    mesh_before_path: str,
    after_mesh_paths: list[str],
    output_dir: str,
    stem: str = "comparison",
) -> tuple[str, list[str]]:
    """Render before preview and multiple after previews (for split ops).

    Returns (before_preview_path, [after_preview_paths]).
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    before_path = str(out / f"{stem}_before.png")
    render_preview(mesh_before_path, before_path)

    after_paths: list[str] = []
    for i, after_path in enumerate(after_mesh_paths):
        preview_path = str(out / f"{stem}_after_{i}.png")
        render_preview(after_path, preview_path)
        after_paths.append(preview_path)

    return before_path, after_paths


def select_highlight_views(
    mesh_before: trimesh.Trimesh,
    mesh_after: trimesh.Trimesh,
) -> list[ViewAngle]:
    """Select view angles that highlight regions of maximum geometric change.

    Returns STANDARD_VIEWS plus any additional highlight angles.
    """
    views = list(STANDARD_VIEWS)

    try:
        # Find region of maximum vertex displacement
        if len(mesh_before.vertices) == len(mesh_after.vertices):
            diff = np.asarray(mesh_after.vertices) - np.asarray(mesh_before.vertices)
            displacements = np.linalg.norm(diff, axis=1)
            max_idx = int(np.argmax(displacements))
            if displacements[max_idx] > 1e-6:
                changed_center = np.asarray(mesh_after.vertices[max_idx])
                centroid = np.asarray(mesh_after.centroid)
                direction = changed_center - centroid
                if np.linalg.norm(direction) > 1e-6:
                    direction = direction / np.linalg.norm(direction)
                    azimuth = float(np.degrees(np.arctan2(direction[1], direction[0])))
                    elev = float(np.degrees(np.arcsin(np.clip(direction[2], -1, 1))))
                    views.append(ViewAngle(name="highlight", elevation=elev, azimuth=azimuth))
        else:
            # Different vertex counts — find centroid of changed region
            # Use bounding box diff as a proxy
            bb_before = mesh_before.bounding_box.bounds
            bb_after = mesh_after.bounding_box.bounds
            center_diff = (bb_after[0] + bb_after[1]) / 2 - (bb_before[0] + bb_before[1]) / 2
            if np.linalg.norm(center_diff) > 1e-6:
                direction = center_diff / np.linalg.norm(center_diff)
                azimuth = float(np.degrees(np.arctan2(direction[1], direction[0])))
                elev = float(np.degrees(np.arcsin(np.clip(direction[2], -1, 1))))
                views.append(ViewAngle(name="highlight", elevation=elev, azimuth=azimuth))
    except Exception:
        logger.debug("Could not compute highlight view angle", exc_info=True)

    return views


def render_split_comparison(
    parts: list[str],
    original_preview_path: str,
    output_dir: str,
    stem: str = "split",
) -> list[str]:
    """Render each split part individually plus an exploded overview.

    Returns list of preview paths (one per part).
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    preview_paths: list[str] = []
    for i, part_path in enumerate(parts):
        preview_path = str(out / f"{stem}_part_{i}.png")
        render_preview(part_path, preview_path)
        preview_paths.append(preview_path)

    return preview_paths
