"""Mesh loading and single-view rendering via matplotlib mplot3d.

Uses the Agg backend for headless rendering — no GPU, no display
server, no OpenGL required.
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from print3d_skill.exceptions import MeshLoadError, UnsupportedFormatError
from print3d_skill.models.mesh import BoundingBox, MeshFile
from print3d_skill.models.preview import ViewAngle

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


def _detect_units(bbox: BoundingBox) -> tuple[str, str | None]:
    """Heuristic unit detection based on bounding box dimensions.

    Returns (detected_units, warning_message_or_None).
    """
    max_dim = bbox.max_dimension

    if max_dim < 0.5:
        return "meters", (
            f"Model dimensions very small (max {max_dim:.3f}). "
            "This may be in meters — consider scaling by 1000 for mm."
        )

    if max_dim > 2000:
        return "unknown", (
            f"Model dimensions very large (max {max_dim:.0f}). "
            "Units may be microns or the model may be invalid."
        )

    # Check for possible inches: common inch sizes map to 25.4mm multiples
    dims = bbox.dimensions
    inch_candidates = [d / 25.4 for d in dims if d > 0]
    common_inch_sizes = {0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0}
    inch_matches = sum(
        1 for ic in inch_candidates
        if any(abs(ic - s) < 0.1 for s in common_inch_sizes)
    )
    if inch_matches >= 2:
        return "inches", (
            "Model dimensions suggest inches rather than mm. "
            "Consider scaling by 25.4 for mm."
        )

    return "mm", None


def load_mesh(path: str) -> MeshFile:
    """Load a mesh file and extract metadata.

    Raises:
        FileNotFoundError: path does not exist
        MeshLoadError: file is corrupt or unreadable
        UnsupportedFormatError: format not recognized
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Mesh file not found: {path}")

    fmt = _detect_format(path)
    file_size = os.path.getsize(path)

    try:
        mesh = trimesh.load(path, force="mesh")
    except Exception as e:
        raise MeshLoadError(f"Failed to load mesh '{path}': {e}") from e

    if not hasattr(mesh, "faces") or len(mesh.faces) == 0:
        raise MeshLoadError(f"Mesh '{path}' has no faces (empty mesh)")

    vertices = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.faces)

    if not np.all(np.isfinite(vertices)):
        raise MeshLoadError(f"Mesh '{path}' contains NaN or infinite vertex coordinates")

    bbox = BoundingBox(
        min_point=tuple(vertices.min(axis=0).tolist()),
        max_point=tuple(vertices.max(axis=0).tolist()),
    )

    detected_units, unit_warning = _detect_units(bbox)

    face_normals = None
    if hasattr(mesh, "face_normals"):
        face_normals = np.asarray(mesh.face_normals)

    return MeshFile(
        path=str(Path(path).resolve()),
        format=fmt,
        vertices=vertices,
        faces=faces,
        face_count=len(faces),
        vertex_count=len(vertices),
        bounding_box=bbox,
        detected_units=detected_units,
        unit_warning=unit_warning,
        file_size_bytes=file_size,
        face_normals=face_normals,
    )


def render_single_view(
    mesh_file: MeshFile,
    view: ViewAngle,
    ax: plt.Axes,
) -> None:
    """Render a single view of a mesh onto a matplotlib 3D axes.

    Builds a Poly3DCollection from faces with face-normal-based
    diffuse coloring and sets the camera elevation/azimuth.
    """
    vertices = mesh_file.vertices
    faces = mesh_file.faces

    # Build polygon collection from faces
    polygons = vertices[faces]

    # Compute face colors from normals (simple diffuse shading)
    if mesh_file.face_normals is not None:
        normals = mesh_file.face_normals
    else:
        # Compute normals manually
        v0 = vertices[faces[:, 0]]
        v1 = vertices[faces[:, 1]]
        v2 = vertices[faces[:, 2]]
        normals = np.cross(v1 - v0, v2 - v0)
        norms = np.linalg.norm(normals, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normals = normals / norms

    # Simple directional light from upper-right-front
    light_dir = np.array([0.5, 0.3, 0.8])
    light_dir = light_dir / np.linalg.norm(light_dir)
    intensity = np.clip(np.dot(normals, light_dir), 0.15, 1.0)

    # Map intensity to blue-gray color scheme
    face_colors = np.zeros((len(faces), 4))
    face_colors[:, 0] = 0.35 + 0.45 * intensity  # R
    face_colors[:, 1] = 0.45 + 0.40 * intensity  # G
    face_colors[:, 2] = 0.55 + 0.35 * intensity  # B
    face_colors[:, 3] = 1.0  # alpha

    collection = Poly3DCollection(polygons, facecolors=face_colors, edgecolors="none")
    ax.add_collection3d(collection)

    # Set axis limits from bounding box
    bbox = mesh_file.bounding_box
    margin = mesh_file.bounding_box.max_dimension * 0.05
    ax.set_xlim(bbox.min_point[0] - margin, bbox.max_point[0] + margin)
    ax.set_ylim(bbox.min_point[1] - margin, bbox.max_point[1] + margin)
    ax.set_zlim(bbox.min_point[2] - margin, bbox.max_point[2] + margin)

    # Set camera angle
    ax.view_init(elev=view.elevation, azim=view.azimuth)

    # Clean up axes
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_zlabel("")
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.set_zticklabels([])
    ax.set_title(view.name, fontsize=10, pad=2)

    # Equal aspect ratio
    max_range = mesh_file.bounding_box.max_dimension / 2
    mid = [
        (bbox.min_point[i] + bbox.max_point[i]) / 2
        for i in range(3)
    ]
    ax.set_xlim(mid[0] - max_range, mid[0] + max_range)
    ax.set_ylim(mid[1] - max_range, mid[1] + max_range)
    ax.set_zlim(mid[2] - max_range, mid[2] + max_range)
