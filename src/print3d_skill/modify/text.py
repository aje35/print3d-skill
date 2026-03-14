"""Text engraving/embossing via OpenSCAD (extended tier).

Generates 3D text geometry using OpenSCAD's text() + linear_extrude(),
then positions it on a target surface and booleans it onto the model.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile

import numpy as np
import trimesh

from print3d_skill.exceptions import CapabilityUnavailable
from print3d_skill.models.modify import SurfaceFace, TextMode, TextParams
from print3d_skill.modify.boolean import boolean_difference, boolean_union

logger = logging.getLogger(__name__)

MIN_FONT_SIZE_MM = 3.0  # Below this, text is likely illegible on FDM


def _check_openscad() -> str:
    """Check OpenSCAD availability and return its path."""
    path = shutil.which("openscad")
    if not path:
        raise CapabilityUnavailable(
            capability="text_engraving",
            provider="OpenSCAD",
            install_instructions=(
                "Install OpenSCAD: brew install openscad (macOS), "
                "apt install openscad (Ubuntu)"
            ),
        )
    return path


def generate_text_mesh(
    text: str,
    font: str = "Liberation Sans",
    font_size: float = 10.0,
    depth: float = 0.6,
) -> trimesh.Trimesh:
    """Generate a 3D text mesh using OpenSCAD."""
    _check_openscad()

    # Escape special characters in text for OpenSCAD
    escaped_text = text.replace("\\", "\\\\").replace('"', '\\"')

    scad_code = (
        f'linear_extrude(height={depth})\n'
        f'  text("{escaped_text}", size={font_size}, font="{font}", '
        f'halign="center", valign="center");\n'
    )

    tmp_dir = tempfile.mkdtemp(prefix="print3d_text_")
    scad_path = os.path.join(tmp_dir, "text.scad")
    stl_path = os.path.join(tmp_dir, "text.stl")

    with open(scad_path, "w") as f:
        f.write(scad_code)

    result = subprocess.run(
        ["openscad", "-o", stl_path, scad_path],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0 or not os.path.exists(stl_path):
        raise RuntimeError(f"OpenSCAD text generation failed:\n{result.stderr}")

    mesh = trimesh.load(stl_path, force="mesh")
    return mesh


def position_text_on_surface(
    text_mesh: trimesh.Trimesh,
    target_mesh: trimesh.Trimesh,
    surface: SurfaceFace,
    position: tuple[float, float] = (0.0, 0.0),
) -> trimesh.Trimesh:
    """Position text mesh on a surface of the target's bounding box."""
    result = text_mesh.copy()
    t_bounds = target_mesh.bounds
    t_min, t_max = t_bounds[0], t_bounds[1]
    t_center = (t_min + t_max) / 2

    # Text is generated in XY plane, extruded along Z
    # We need to rotate and translate it to sit on the target surface
    transform = np.eye(4)

    if surface == SurfaceFace.TOP:
        # Text sits on top face, looking up (+Z)
        transform[:3, 3] = [t_center[0] + position[0], t_center[1] + position[1], t_max[2]]
    elif surface == SurfaceFace.BOTTOM:
        # Flip text and place on bottom
        transform[:3, :3] = [[1, 0, 0], [0, 1, 0], [0, 0, -1]]
        transform[:3, 3] = [t_center[0] + position[0], t_center[1] + position[1], t_min[2]]
    elif surface == SurfaceFace.FRONT:
        # Rotate to face front (-Y)
        transform[:3, :3] = [[1, 0, 0], [0, 0, 1], [0, -1, 0]]
        transform[:3, 3] = [t_center[0] + position[0], t_min[1], t_center[2] + position[1]]
    elif surface == SurfaceFace.BACK:
        # Rotate to face back (+Y)
        transform[:3, :3] = [[-1, 0, 0], [0, 0, -1], [0, -1, 0]]
        transform[:3, 3] = [t_center[0] + position[0], t_max[1], t_center[2] + position[1]]
    elif surface == SurfaceFace.LEFT:
        # Rotate to face left (-X)
        transform[:3, :3] = [[0, 0, -1], [0, 1, 0], [1, 0, 0]]
        transform[:3, 3] = [t_min[0], t_center[1] + position[0], t_center[2] + position[1]]
    elif surface == SurfaceFace.RIGHT:
        # Rotate to face right (+X)
        transform[:3, :3] = [[0, 0, 1], [0, 1, 0], [-1, 0, 0]]
        transform[:3, 3] = [t_max[0], t_center[1] + position[0], t_center[2] + position[1]]

    result.apply_transform(transform)
    return result


def project_text_to_curved_surface(
    text_mesh: trimesh.Trimesh,
    target_mesh: trimesh.Trimesh,
    surface: SurfaceFace,
) -> trimesh.Trimesh:
    """Project text onto simple analytic curved surfaces (cylinders, spheres).

    For non-analytic surfaces, returns text at flat plane position with a warning.
    """
    result = text_mesh.copy()

    # Detect if target is approximately cylindrical or spherical
    bounds = target_mesh.bounds
    dims = bounds[1] - bounds[0]
    center = (bounds[0] + bounds[1]) / 2

    # Check for cylindrical shape (two similar dims, one different)
    sorted_dims = sorted(dims)
    ratio = sorted_dims[0] / max(sorted_dims[1], 1e-10)

    if ratio > 0.8:  # All dims similar = possibly spherical
        radius = float(np.mean(dims)) / 2.0
        verts = np.asarray(result.vertices)
        for i in range(len(verts)):
            v = verts[i] - center
            dist = np.linalg.norm(v)
            if dist > 1e-6:
                verts[i] = center + v * (radius / dist)
        result.vertices = verts
    else:
        # Check if cylindrical along the longest axis
        long_axis = int(np.argmax(dims))
        short_axes = [i for i in range(3) if i != long_axis]
        radii = [dims[a] / 2.0 for a in short_axes]
        avg_radius = float(np.mean(radii))

        verts = np.asarray(result.vertices)
        for i in range(len(verts)):
            v = verts[i].copy()
            # Project radially in the cross-section plane
            local = v - center
            r_vec = np.array([
                local[short_axes[0]],
                local[short_axes[1]],
            ])
            r = np.linalg.norm(r_vec)
            if r > 1e-6:
                scale = avg_radius / r
                v[short_axes[0]] = center[short_axes[0]] + r_vec[0] * scale
                v[short_axes[1]] = center[short_axes[1]] + r_vec[1] * scale
            verts[i] = v
        result.vertices = verts

    return result


def execute_text(
    mesh: trimesh.Trimesh,
    params: TextParams,
) -> tuple[trimesh.Trimesh, list[str]]:
    """Execute a text engraving/embossing operation.

    Returns (result_mesh, warnings).
    """
    warnings: list[str] = []

    # Check font size warning
    if params.font_size < MIN_FONT_SIZE_MM:
        warnings.append(
            f"Font size {params.font_size}mm may be too small for FDM printing "
            f"(minimum recommended: {MIN_FONT_SIZE_MM}mm)"
        )

    # Generate text geometry
    text_mesh = generate_text_mesh(
        params.text, params.font, params.font_size, params.depth
    )

    # Position on surface
    text_mesh = position_text_on_surface(
        text_mesh, mesh, params.surface, params.position
    )

    # Boolean operation
    if params.mode == TextMode.ENGRAVE:
        result = boolean_difference(mesh, text_mesh)
    elif params.mode == TextMode.EMBOSS:
        result = boolean_union(mesh, text_mesh)
    else:
        raise ValueError(f"Unknown text mode: {params.mode}")

    return result, warnings
