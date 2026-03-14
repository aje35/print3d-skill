"""Composite 2x2 multi-angle preview renderer.

Renders front, side, top, and isometric views into a single
1600x1200 PNG image using matplotlib's Agg backend.
"""

from __future__ import annotations

import os
import time

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from print3d_skill.models.mesh import MeshFile
from print3d_skill.models.preview import (
    STANDARD_VIEWS,
    MeshSummary,
    PreviewResult,
)
from print3d_skill.rendering.renderer import render_single_view


def compose_preview(
    mesh_file: MeshFile,
    output_path: str,
    resolution: tuple[int, int] = (1600, 1200),
) -> PreviewResult:
    """Render all 4 standard views into a 2x2 grid and save as PNG.

    Returns a PreviewResult with render metadata and any warnings.
    """
    start = time.monotonic()
    warnings: list[str] = []

    if mesh_file.unit_warning:
        warnings.append(mesh_file.unit_warning)

    if mesh_file.face_count > 1_000_000:
        warnings.append(
            f"High face count ({mesh_file.face_count:,}). "
            "Rendering may be slow."
        )

    dpi = 100
    fig_w = resolution[0] / dpi
    fig_h = resolution[1] / dpi
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi)
    fig.patch.set_facecolor("#1a1a2e")

    for idx, view in enumerate(STANDARD_VIEWS):
        ax = fig.add_subplot(2, 2, idx + 1, projection="3d")
        ax.set_facecolor("#16213e")
        render_single_view(mesh_file, view, ax)

    fig.tight_layout(pad=1.0)
    fig.savefig(output_path, dpi=dpi, facecolor=fig.get_facecolor())
    plt.close(fig)

    render_time = time.monotonic() - start
    file_size = os.path.getsize(output_path)

    return PreviewResult(
        image_path=str(os.path.abspath(output_path)),
        resolution=resolution,
        file_size_bytes=file_size,
        views=list(STANDARD_VIEWS),
        mesh_summary=MeshSummary(
            face_count=mesh_file.face_count,
            vertex_count=mesh_file.vertex_count,
            bounding_box_mm=mesh_file.bounding_box.dimensions,
        ),
        warnings=warnings,
        render_time_seconds=render_time,
        timed_out=False,
    )
